# sales/etr.py

def process_fieldmax_etr_for_sale(sale):
    """
    Process sale through Fieldmax ETR.
    Replace this stub with actual API calls.
    """
    return {
        "success": True,
        "receipt_number": f"RCPT-{sale.sale_id}",
        "control_code": "CTRL123456",
    }

def process_etr_for_sale(sale):
    """
    Backup/simple ETR processor
    """
    return {
        "success": True,
        "receipt_number": f"RCPT-{sale.sale_id}",
        "control_code": "CTRL123456",
    }
