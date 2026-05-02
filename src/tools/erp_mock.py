import time


def trigger_erp_action(action_type: str, justification: str) -> bool:
    """
    Simulates a secure outbound API call to an Enterprise Resource Planning system.
    """
    print("\n[ERP MOCK] Authenticating to core manufacturing mainframe...")
    time.sleep(1)
    print(f"[ERP MOCK] Executing command: {action_type}")
    print(f"[ERP MOCK] Attaching audit justification: {justification}")
    time.sleep(1)
    print("[ERP MOCK] 200 OK: Action registered in ERP.\n")
    return True
