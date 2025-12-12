#!/usr/bin/env python3
"""
Job Agent 설치/제거 도구
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

class JobAgentInstaller:
    def __init__(self):
        self.home = Path.home()
        self.install_dir = self.home / ".job_agent"
        self.config_file = self.install_dir / "config.json"
        self.service_file = self.home / "Library/LaunchAgents/com.jobagent.plist"  # macOS
        
    def install(self, api_url="http://localhost:8000"):
        """에이전트 설치"""
        print("🚀 Installing Job Agent...")
        
        # 1. 설치 디렉토리 생성
        self.install_dir.mkdir(exist_ok=True)
        
        # 2. 에이전트 파일 복사
        current_dir = Path(__file__).parent
        shutil.copy2(current_dir / "host_agent.py", self.install_dir / "host_agent.py")
        
        # 3. 설정 파일 생성
        config = {
            "api_url": api_url,
            "log_level": "INFO"
        }
        
        import json
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # 4. 의존성 설치
        print("📦 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "docker", "psutil", "requests"], 
                      check=True)
        
        # 5. macOS 서비스 등록
        self.create_launchd_service()
        
        # 6. 서비스 시작
        self.start_service()
        
        print("✅ Job Agent installed successfully!")
        print(f"📁 Install directory: {self.install_dir}")
        print(f"🔧 Config file: {self.config_file}")
        print(f"🌐 API URL: {api_url}")
        print("\n📋 Commands:")
        print("  job-agent status   - Check status")
        print("  job-agent stop     - Stop agent")
        print("  job-agent start    - Start agent")
        print("  job-agent uninstall - Remove agent")
        
        # 7. CLI 명령어 생성
        self.create_cli_command()
    
    def create_launchd_service(self):
        """macOS LaunchAgent 서비스 생성"""
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jobagent</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{self.install_dir}/host_agent.py</string>
        <string>--config</string>
        <string>{self.config_file}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{self.install_dir}/agent.log</string>
    <key>StandardErrorPath</key>
    <string>{self.install_dir}/agent.error.log</string>
</dict>
</plist>"""
        
        # LaunchAgents 디렉토리 생성
        self.service_file.parent.mkdir(exist_ok=True)
        
        with open(self.service_file, 'w') as f:
            f.write(plist_content)
    
    def create_cli_command(self):
        """CLI 명령어 생성"""
        cli_script = f"""#!/usr/bin/env python3
import subprocess
import sys
import json
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: job-agent <command>")
        print("Commands: status, start, stop, restart, uninstall, config")
        return
    
    command = sys.argv[1]
    service_name = "com.jobagent"
    
    if command == "status":
        result = subprocess.run(["launchctl", "list", service_name], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("🟢 Job Agent is running")
        else:
            print("🔴 Job Agent is not running")
    
    elif command == "start":
        subprocess.run(["launchctl", "load", "{self.service_file}"])
        print("🚀 Job Agent started")
    
    elif command == "stop":
        subprocess.run(["launchctl", "unload", "{self.service_file}"])
        print("⏹️  Job Agent stopped")
    
    elif command == "restart":
        subprocess.run(["launchctl", "unload", "{self.service_file}"])
        subprocess.run(["launchctl", "load", "{self.service_file}"])
        print("🔄 Job Agent restarted")
    
    elif command == "config":
        try:
            with open("{self.config_file}") as f:
                config = json.load(f)
            print("📋 Current configuration:")
            for k, v in config.items():
                print(f"  {{k}}: {{v}}")
        except Exception as e:
            print(f"Error reading config: {{e}}")
    
    elif command == "uninstall":
        print("🗑️  Uninstalling...")
        subprocess.run(["launchctl", "unload", "{self.service_file}"])
        import shutil
        shutil.rmtree("{self.install_dir}", ignore_errors=True)
        Path("{self.service_file}").unlink(missing_ok=True)
        print("✅ Uninstalled")
    
    else:
        print(f"Unknown command: {{command}}")

if __name__ == "__main__":
    main()
"""
        
        cli_path = Path("/usr/local/bin/job-agent")
        try:
            with open(cli_path, 'w') as f:
                f.write(cli_script)
            os.chmod(cli_path, 0o755)
        except PermissionError:
            # 권한 없으면 홈 디렉토리에 생성
            cli_path = self.home / ".local/bin/job-agent"
            cli_path.parent.mkdir(exist_ok=True)
            with open(cli_path, 'w') as f:
                f.write(cli_script)
            os.chmod(cli_path, 0o755)
            print(f"⚠️  CLI installed to {cli_path} (add to PATH)")
    
    def start_service(self):
        """서비스 시작"""
        try:
            subprocess.run(["launchctl", "load", str(self.service_file)], check=True)
            print("🚀 Service started")
        except subprocess.CalledProcessError:
            print("⚠️  Failed to start service automatically")
    
    def uninstall(self):
        """에이전트 제거"""
        print("🗑️  Uninstalling Job Agent...")
        
        # 1. 서비스 중지 및 제거
        try:
            subprocess.run(["launchctl", "unload", str(self.service_file)])
            self.service_file.unlink(missing_ok=True)
        except:
            pass
        
        # 2. 설치 디렉토리 제거
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir)
        
        # 3. CLI 명령어 제거
        cli_paths = [
            Path("/usr/local/bin/job-agent"),
            self.home / ".local/bin/job-agent"
        ]
        for cli_path in cli_paths:
            cli_path.unlink(missing_ok=True)
        
        print("✅ Job Agent uninstalled successfully!")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Job Agent Installer')
    parser.add_argument('command', choices=['install', 'uninstall'], 
                       help='Command to execute')
    parser.add_argument('--api-url', default='http://localhost:8000',
                       help='Job Management API URL')
    
    args = parser.parse_args()
    installer = JobAgentInstaller()
    
    if args.command == 'install':
        installer.install(args.api_url)
    elif args.command == 'uninstall':
        installer.uninstall()

if __name__ == "__main__":
    main()
