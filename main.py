import subprocess
import sys
import time
import os
import webbrowser
import threading

def main():
    print("==========================================================")
    print("🎓 AI CELL CLASSROOM PERFORMANCE & ANALYTICS SUITE")
    print("   FastAPI Server & Web Application for Professors")
    print("==========================================================")

    # CLI Mode
    if "--cli" in sys.argv:
        print("🎥 Running CLI Video Pipeline...")
        from pipeline import run_pipeline
        sample_path = "classroom3.mp4" if os.path.exists("classroom3.mp4") else 0
        run_pipeline(source=sample_path, max_seconds=60)
        
        print("📊 Generating Reports & PDF Audit...")
        import generate_reports
        import visualize
        print("✨ CLI Processing Complete!")
        return

    # Streamlit Mode
    if "--streamlit" in sys.argv:
        print("📡 Launching Streamlit App...")
        subprocess.run(["python3", "-m", "streamlit", "run", "app.py"])
        return

    # Default Mode: Launch FastAPI Server & Open Web App
    host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") or os.environ.get("RENDER") else "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"

    print(f"\n🚀 Launching FastAPI Server on {url} (binding {host}:{port}) ...")

    # Open browser asynchronously only in local desktop mode
    if not os.environ.get("PORT") and not os.environ.get("RENDER") and not os.environ.get("HEADLESS"):
        print("🌐 Opening Web App in default browser...")
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    print("👉 Press Ctrl+C in this terminal window to stop the server.\n")

    try:
        import uvicorn
        from server import app
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        print("\n🛑 Server shut down gracefully.")
    except Exception as e:
        print(f"\n❌ Server Error: {e}")

if __name__ == "__main__":
    main()