#!/usr/bin/env python3
"""
UAF V32 Command Hub - Initialization Monitor
실시간으로 커넥터 초기화 상태를 모니터링합니다.
"""
import httpx
import time
import sys

API_URL = "http://localhost:8000/v32/connectors/initialization-status"
SPINNER = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

def get_status():
    """API에서 초기화 상태 가져오기"""
    try:
        response = httpx.get(API_URL, timeout=5.0)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

def print_status(status_data, spinner_idx, elapsed):
    """상태 출력"""
    print("\033[2J\033[H")  # 화면 클리어
    print("=" * 60)
    print("UAF V32 Command Hub - Initialization Monitor")
    print("=" * 60)
    
    if not status_data:
        print(f"{SPINNER[spinner_idx]} Waiting for API server...")
        return False
    
    connectors = status_data.get("connectors", {})
    all_ready = True
    
    # EDGAR 상태
    edgar = connectors.get("edgar", {})
    edgar_status = edgar.get("status", "unknown")
    if edgar_status == "ready":
        print("✅ EDGAR: Ready")
        details = edgar.get("details", {})
        if "rate_limiting" in details:
            print(f"   {details['rate_limiting']}")
    elif edgar_status == "failed":
        print("❌ EDGAR: Failed")
        all_ready = False
    else:
        print(f"{SPINNER[spinner_idx]} EDGAR: {edgar_status}")
        all_ready = False
    
    # DART 상태
    dart = connectors.get("dart", {})
    dart_status = dart.get("status", "unknown")
    if dart_status == "ready":
        print("✅ DART: Ready")
        details = dart.get("details", {})
        if "companies_loaded" in details:
            print(f"   {details['companies_loaded']:,} companies loaded")
    elif dart_status == "initializing":
        print(f"{SPINNER[spinner_idx]} DART: Initializing... ({elapsed}s)")
        print("   💡 DART initialization takes 30-60 seconds due to large dataset")
        all_ready = False
    elif dart_status == "failed":
        print("❌ DART: Failed")
        details = dart.get("details", {})
        if "error" in details:
            print(f"   Error: {details['error']}")
        all_ready = False
    else:
        print(f"{SPINNER[spinner_idx]} DART: {dart_status}")
        all_ready = False
    
    print()
    if all_ready:
        print(f"🎉 All connectors initialized! (took {elapsed} seconds)")
        print()
        print("You can now use:")
        print("  - EDGAR: /v32/connectors/edgar/*")
        print("  - DART: /v32/data/dart/*")
        return True
    else:
        print(f"⏳ Initialization in progress... ({elapsed}s)")
        return False

def main():
    """메인 모니터링 루프"""
    print("Starting UAF V32 initialization monitor...")
    print("Press Ctrl+C to exit\n")
    
    spinner_idx = 0
    start_time = time.time()
    
    try:
        while True:
            elapsed = int(time.time() - start_time)
            status_data = get_status()
            
            if print_status(status_data, spinner_idx, elapsed):
                # 모든 초기화 완료
                break
            
            spinner_idx = (spinner_idx + 1) % len(SPINNER)
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
