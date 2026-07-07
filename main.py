"""
Serviciu de facturare Wix -> SmartBill.
Primește comanda de la butonul din pagina de AWB (sau alt apelant) și creează factura
(ciornă cât timp DRY_RUN=true).
"""
import logging

from fastapi import FastAPI, Request, Header, HTTPException

import config
import storage
import wix_mapper
from smartbill import SmartBillClient, SmartBillError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("wix-smartbill")

app = FastAPI(title="Wix -> SmartBill invoicing")

sb = SmartBillClient(
    user=config.SMARTBILL_USER,
    token=config.SMARTBILL_TOKEN,
    company_vat=config.SMARTBILL_COMPANY_VAT,
)


@app.get("/")
def health():
    return {"status": "ok", "dry_run": config.DRY_RUN}


@app.post("/factura")
async def factura(request: Request, x_webhook_secret: str = Header(default=None)):
    # 1. Autentificare: doar request-uri semnate cu secretul nostru
    if x_webhook_secret != config.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Secret invalid")

    order = await request.json()
    oid = wix_mapper.order_id(order)
    if not oid:
        raise HTTPException(status_code=400, detail="Comandă fără id")

    # 2. Idempotență: dacă am facturat deja comanda, nu repetăm
    existing = storage.already_invoiced(oid)
    if existing:
        log.info("Comanda %s deja facturată (%s%s)", oid, existing["series"], existing["number"])
        return {"status": "skip", "reason": "already_invoiced", "invoice": existing}

    # 3. Construim payload-ul și emitem factura / ciorna
    payload = wix_mapper.build_invoice_payload(order)
    try:
        result = sb.create_invoice(payload)
    except SmartBillError as e:
        log.error("Eroare SmartBill pentru comanda %s: %s", oid, e)
        raise HTTPException(status_code=502, detail=str(e))

    series = result.get("series", config.SMARTBILL_SERIES)
    number = str(result.get("number", ""))
    url = result.get("url", "") or ""
    storage.mark_invoiced(oid, series, number)
    log.info("Factură creată pentru comanda %s -> %s%s (draft=%s)", oid, series, number, config.DRY_RUN)

    return {
        "status": "ok",
        "order_id": oid,
        "invoice": {"series": series, "number": number, "url": url},
    }
