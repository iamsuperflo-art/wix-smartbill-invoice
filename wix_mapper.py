"""
Mapare comandă Wix (obiectul returnat de orders.getOrder în Velo) -> payload SmartBill.

ATENȚIE: structura exactă a obiectului `order` variază (variante de produs, cupoane,
transport gratuit etc.). Acest fișier folosește câmpurile DOCUMENTATE ale Wix eCom Orders,
dar trebuie verificat pe o comandă reală a magazinului. Locurile de verificat sunt marcate
cu # VERIFICĂ.
"""
import config


def _amount(node, default=0.0) -> float:
    """Wix întoarce sume ca string ('90.00') în .amount. Le normalizăm la float."""
    if node is None:
        return default
    if isinstance(node, dict):
        node = node.get("amount", default)
    try:
        return float(node)
    except (TypeError, ValueError):
        return default


def _get(order, *keys, default=None):
    """Acces sigur prin chei imbricate: _get(order, 'priceSummary', 'total')."""
    cur = order
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def _client_from_order(order: dict) -> dict:
    billing = order.get("billingInfo", {}) or {}
    contact = billing.get("contactDetails", {}) or {}
    address = billing.get("address", {}) or {}

    first = contact.get("firstName", "") or ""
    last = contact.get("lastName", "") or ""
    company = contact.get("company")  # firmă, dacă a fost completat
    vat_id = contact.get("vatId", {})  # ex: {"id": "RO123", "type": "EU_VAT"}  # VERIFICĂ
    vat_code = vat_id.get("id") if isinstance(vat_id, dict) else (vat_id or None)

    email = (
        contact.get("email")
        or _get(order, "buyerInfo", "email")
        or ""
    )

    is_company = bool(company or vat_code)

    client = {
        "name": company if is_company else f"{first} {last}".strip() or "Client",
        "address": address.get("addressLine1", "") or address.get("addressLine", ""),
        "city": address.get("city", ""),
        "county": address.get("subdivisionFullname") or address.get("subdivision", ""),  # VERIFICĂ
        "country": address.get("countryFullname") or address.get("country", "Romania"),
        "email": email,
        "isTaxPayer": is_company,
        "saveToDb": False,
    }
    if is_company and vat_code:
        client["vatCode"] = vat_code
    return client


def _vat_percent_for_line(line: dict) -> float:
    """
    Încearcă să citească cota de TVA a liniei. Wix poate expune taxRate ca '0.21' sau '21'.
    IMPORTANT: magazinul NU are taxe configurate în Wix, deci taxRate vine '0'.
    0 sau lipsă => folosim DEFAULT_VAT_PERCENT (SmartBill nu are cotă 'Normala 0%').
    """
    rate = _get(line, "taxInfo", "taxRate") or _get(line, "tax", "rate")
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        return config.DEFAULT_VAT_PERCENT
    if rate <= 0:
        return config.DEFAULT_VAT_PERCENT
    # normalizează 0.21 -> 21
    return rate * 100 if rate <= 1 else rate


def build_invoice_payload(order: dict) -> dict:
    currency = order.get("currency", "RON")
    # Prețurile de pe site sunt finale (cu TVA inclus). Nu ne bazăm pe
    # order.taxIncludedInPrices: fără taxe configurate în Wix, vine False
    # și SmartBill ar adăuga TVA PESTE prețul de pe site.
    tax_included = True

    products = []
    for line in order.get("lineItems", []):
        name = _get(line, "productName", "original") or line.get("productName") or "Produs"
        qty = float(line.get("quantity", 1))
        # preț unitar; câmpul exact poate diferi (price / priceBeforeDiscounts) # VERIFICĂ
        unit_price = _amount(line.get("price"))
        sku = _get(line, "physicalProperties", "sku") or _get(line, "catalogReference", "catalogItemId") or ""
        vat = _vat_percent_for_line(line)

        products.append({
            "name": name,
            "code": sku,
            "measuringUnitName": "buc",
            "currency": currency,
            "quantity": qty,
            "price": unit_price,
            "isTaxIncluded": tax_included,
            "taxName": config.DEFAULT_VAT_NAME,
            "taxPercentage": vat,
        })

    # Transport ca linie separată, dacă există
    shipping = _amount(_get(order, "priceSummary", "shipping"))
    if shipping > 0:
        products.append({
            "name": "Transport",
            "measuringUnitName": "buc",
            "currency": currency,
            "quantity": 1,
            "price": shipping,
            "isTaxIncluded": tax_included,
            "taxName": config.DEFAULT_VAT_NAME,
            "taxPercentage": config.DEFAULT_VAT_PERCENT,
        })

    # NOTĂ discount: dacă magazinul folosește cupoane la nivel de comandă (nu pe linie),
    # totalul SmartBill nu va bate cu Wix. În acel caz trebuie adăugată o linie de discount
    # sau distribuit discountul pe produse. Tratăm asta după ce vedem o comandă reală cu cupon.

    issue_date = (order.get("_createdDate") or order.get("createdDate") or "")[:10]  # YYYY-MM-DD

    return {
        "companyVatCode": config.SMARTBILL_COMPANY_VAT,
        "seriesName": config.SMARTBILL_SERIES,
        "isDraft": config.DRY_RUN,
        "client": _client_from_order(order),
        "issueDate": issue_date,
        "products": products,
    }


def order_id(order: dict) -> str:
    return str(order.get("_id") or order.get("id") or order.get("number") or "")
