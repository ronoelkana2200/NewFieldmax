def build_receipt_payload(sale, client, items_qs):
    """
    Build JSON payload for Tremol S21/M23 fiscal receipt.

    Arguments:
    - sale: Sale instance
    - client: dict from sale.client_details
    - items_qs: SaleItem queryset
    """
    items = [
        {
            "sku": item.batch.sku_code,
            "name": item.product.name,
            "qty": item.quantity,
            "price": float(item.price),
            "total": float(item.subtotal())
        }
        for item in items_qs
    ]

    return {
        "operator": sale.seller.username if sale.seller else "Unknown",
        "receiptNumber": sale.sale_id,
        "client": {
            "name": client.get("name", ""),
            "phone": client.get("phone", ""),
            "idNumber": client.get("id_no", ""),
            "nokName": client.get("nok_name", ""),
            "nokPhone": client.get("nok_phone", "")
        },
        "items": items,
        "footer": [
            "FIELDMAX SUPPLIERS LTD",
            "Address: Nairobi-Kenya",
            "Tel:+254722527955 or +254722527955",
            "Goods Once Sold Cannot Be Re-Accepted!"
        ]
    }
