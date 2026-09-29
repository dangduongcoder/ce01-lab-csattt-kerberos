.PHONY: up down restart logs healthcheck demo-normal demo-attack inspect detect recover demo-all clean help

help:
	@echo "=========================================================="
	@echo "    Kerberos & Active Directory Golden Ticket Lab        "
	@echo "=========================================================="
	@echo "Các lệnh điều khiển môi trường:"
	@echo "  make up           - Build và khởi động 4 container lab"
	@echo "  make down         - Dừng tất cả container"
	@echo "  make restart      - Khởi động lại các dịch vụ"
	@echo "  make logs         - Xem log real-time của hệ thống"
	@echo "  make healthcheck  - Kiểm tra trạng thái KDC, DNS, API"
	@echo ""
	@echo "Các lệnh Demo kịch bản BTL:"
	@echo "  make demo-normal  - [Màn 2] Xác thực Kerberos chuẩn (Alice)"
	@echo "  make demo-attack  - [Màn 3] Tấn công Golden Ticket (Attacker)"
	@echo "  make inspect      - [Màn 4] Phẫu thuật vé Kerberos & PAC"
	@echo "  make detect       - [Màn 5] Giám sát & Báo động (Blue Team)"
	@echo "  make recover      - [Màn 6] Khắc phục bằng Double Reset krbtgt"
	@echo "  make demo-all     - Chạy tự động liên hoàn toàn bộ kịch bản"
	@echo "  make clean        - Xóa sạch container & volume (Reset lab)"
	@echo "=========================================================="

up:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

healthcheck:
	@chmod +x scripts/*.sh
	@./scripts/healthcheck.sh

demo-normal:
	docker compose exec client python demo_normal.py

demo-attack:
	docker compose exec attacker python demo_golden_ticket.py

inspect:
	docker compose exec client python inspect_ticket.py

detect:
	docker compose exec client python -m detector.report

recover:
	docker compose exec dc /scripts/rotate_krbtgt.sh

demo-all:
	@chmod +x scripts/*.sh
	@./scripts/demo_all.sh

clean:
	@chmod +x scripts/*.sh
	@./scripts/reset.sh
