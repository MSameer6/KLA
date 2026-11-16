from decimal import Decimal

from .models import ClientInvoice


SERVICE_FEES = {
    "needs_ntn_return": {
        "label": "NTN & Return Filing",
        "amount": Decimal("5000.00"),
        "description": "PKR 5,000 (discounted from PKR 7,000)",
    },
    "needs_sales_tax": {
        "label": "Sales Tax",
        "amount": Decimal("20000.00"),
        "description": "PKR 20,000/month; first month",
    },
    "needs_income_tax": {
        "label": "Income Tax",
        "amount": Decimal("20000.00"),
        "description": "PKR 20,000",
    },
}


def create_initial_service_invoice(client, selected_services):
    line_items = []
    total = Decimal("0.00")
    for field_name, fee in SERVICE_FEES.items():
        if selected_services.get(field_name):
            line_items.append(f"{fee['label']} ({fee['description']})")
            total += fee["amount"]

    if not line_items:
        return None

    description = "Initial service fees: " + "; ".join(line_items)
    existing_invoice = ClientInvoice.objects.filter(
        client=client,
        description=description,
    ).first()
    if existing_invoice:
        return existing_invoice

    return ClientInvoice.objects.create(
        client=client,
        description=description,
        amount=total,
    )
