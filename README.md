# 🛡️ Kerberos Active Directory Lab — Golden Ticket Demonstration

Dự án mô phỏng môi trường phòng thí nghiệm (Lab) bảo mật hoàn chỉnh, độc lập và di động bằng Docker phục vụ bài tập lớn môn **Cơ sở An toàn Thông tin (CSATTT)**. 

Chủ đề: **Quy trình xác thực Kerberos, Khai thác Tấn công Golden Ticket (MITRE ATT&CK T1558.001), Giám sát phát hiện (Blue Team) và Khắc phục sự cố (Incident Response).**

Hỗ trợ hoạt động trơn tru trên **macOS (Apple Silicon arm64 & Intel)**, **Linux (Ubuntu/Debian/Fedora)** và **Windows (WSL2 / Docker Desktop)**.

---

## 📑 Mục lục
1. [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
2. [Cơ sở lý thuyết](#-cơ-sở-lý-thuyết)
   * [Quy trình xác thực Kerberos](#1-quy-trình-xác-thực-kerberos-chuẩn)
   * [Bản chất cuộc tấn công Golden Ticket](#2-bản-chất-cuộc-tấn-công-golden-ticket)
   * [Cấu trúc phiếu xác thực và PAC](#3-cấu-trúc-phiếu-xác-thực-và-pac-privilege-attribute-certificate)
   * [Quy tắc phát hiện bất thường](#4-các-quy-tắc-phát-hiện-blue-team-detection)
   * [Cơ chế khôi phục Double krbtgt Reset](#5-tại-sao-phải-double-reset-krbtgt)
3. [Cài đặt & Khởi động](#-cài-đặt--khởi-động)
4. [Kịch bản Demo trực tiếp (5 Màn)](#-kịch-bản-demo-trực-tiếp-5-màn)
5. [Cấu trúc mã nguồn](#-cấu-trúc-mã-nguồn)
6. [Xử lý sự cố thường gặp (Troubleshooting)](#-xử-lý-sự-cố-thường-gặp)

---

## 🏛️ Kiến trúc hệ thống

Hệ thống gồm 4 container chạy trong mạng nội bộ cô lập `172.30.0.0/24` với domain giả lập `LAB.LOCAL`:

```text
                             Docker Internal Network: 172.30.0.0/24
                                      Domain: LAB.LOCAL

                             ┌───────────────────────────────┐
                             │       DC / KDC Container      │
                             │         172.30.0.10           │
                             │                               │
                             │  • Samba 4 Active Directory   │
                             │  • Kerberos KDC (Port 88)     │
                             │  • Internal DNS (Port 53)     │
                             │  • LDAP Directory (Port 389)  │
                             └───────────────┬───────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             │                               │                               │
             ▼                               ▼                               ▼
   ┌───────────────────┐           ┌───────────────────┐           ┌───────────────────┐
   │  Client Container │           │ API Server (Svc)  │           │ Attacker Container│
   │    172.30.0.30    │           │    172.30.0.20    │           │    172.30.0.50    │
   │                   │           │                   │           │                   │
   │ • Python CLI      │           │ • FastAPI REST API│           │ • Impacket Suite  │
   │ • pyspnego/gssapi │           │ • SPNEGO Auth     │           │ • Ticket Forger   │
   │ • Ticket Inspector│           │ • SPN HTTP/api... │           │ • Audit Bypass    │
   │ • Normal User     │           │ • Port 8000       │           │ • Golden Ticket   │
   └───────────────────┘           └───────────────────┘           └───────────────────┘
             │                               ▲                               ▲
             └────── Normal Auth (SPNEGO) ───┘                               │
                                                                             │
             └────────────────── Forged Golden Ticket (Bypass KDC) ──────────┘
```

| Container | Hostname | IP | Vai trò & Công nghệ |
| :--- | :--- | :--- | :--- |
| `kerberos-dc` | `dc.lab.local` | `172.30.0.10` | Samba 4 AD DC, KDC, LDAP, Internal DNS. |
| `kerberos-api` | `api.lab.local` | `172.30.0.20` | FastAPI Server xác thực qua Kerberos SPNEGO bằng Keytab. |
| `kerberos-client` | `client.lab.local` | `172.30.0.30` | Máy người dùng hợp lệ (`alice`), tích hợp CLI và Tool phân tích vé. |
| `kerberos-attacker`| `attacker.lab.local`| `172.30.0.50` | Máy giả lập kẻ tấn công, sử dụng Impacket rèn Golden Ticket. |

---

## 📚 Cơ sở lý thuyết

### 1. Quy trình xác thực Kerberos chuẩn
Giao thức Kerberos hoạt động theo nguyên lý "Vé bên thứ ba đáng tin cậy" (Trusted Third-Party KDC) gồm 3 pha trao đổi:

1. **Pha 1: Xác thực với KDC (AS Exchange)**
   * $AS\text{-}REQ$: Client gửi yêu cầu kèm Pre-Authentication (Timestamp mã hóa bằng mật khẩu của User).
   * $AS\text{-}REP$: KDC kiểm tra mật khẩu. Nếu hợp lệ, KDC cấp **TGT (Ticket Granting Ticket)** được mã hóa bằng khóa bí mật của tài khoản đặc biệt `krbtgt`.
2. **Pha 2: Xin vé dịch vụ (TGS Exchange)**
   * $TGS\text{-}REQ$: Client gửi TGT lên KDC xin vé truy cập dịch vụ `HTTP/api.lab.local`.
   * $TGS\text{-}REP$: KDC dùng khóa `krbtgt` để giải mã TGT. Khi thấy TGT hợp lệ, KDC cấp **Service Ticket** được mã hóa bằng khóa riêng của chính dịch vụ đó (lưu trong Keytab).
3. **Pha 3: Xác thực với dịch vụ (AP Exchange)**
   * $AP\text{-}REQ$: Client gửi HTTP Header `Authorization: Negotiate <Service Ticket>` tới API Server.
   * $AP\text{-}REP$: API Server dùng Keytab của mình để giải mã vé và xác nhận danh tính người dùng.

---

### 2. Bản chất cuộc tấn công Golden Ticket
* **Golden Ticket KHÔNG PHẢI là tấn công Brute-force mật khẩu.**
* Đây là kỹ thuật tạo vé giả mạo ở tầng kiến trúc mật mã:
  1. Trong Active Directory, tài khoản `krbtgt` là tài khoản hệ thống dùng để mã hóa và ký toàn bộ các vé TGT trong Domain.
  2. Nếu kẻ tấn công chiếm được khóa bí mật (NTLM Hash hoặc AES-256 Key) của `krbtgt` và Domain SID, **kẻ tấn công có thể tự đóng vai trò KDC**.
  3. Attacker tự rèn một vé TGT mang tên bất kỳ (kể cả `administrator` hay user không tồn tại), tự cấp quyền `Domain Admins` (RID 512), đặt hạn dùng 10 năm, và mã hóa vé đó bằng chính khóa `krbtgt`.
  4. Khi attacker gửi vé này lên KDC hoặc dịch vụ, hệ thống giải mã bằng khóa `krbtgt` thấy hoàn toàn hợp lệ nên **tin tưởng tuyệt đối**.

---

### 3. Cấu trúc phiếu xác thực và PAC (Privilege Attribute Certificate)
Bên trong vé Kerberos có cấu trúc PAC chứa thông tin phân quyền của người dùng:

| Thuộc tính (Attribute) | Vé hợp lệ của Alice | Vé Golden Ticket (Attacker) |
| :--- | :--- | :--- |
| **Client Principal** | `alice@LAB.LOCAL` | `administrator@LAB.LOCAL` |
| **User RID** | `1104` (Regular User) | `500` (Default Administrator) |
| **Group Memberships (PAC)** | `Domain Users (513)` | `Domain Admins (512)`, `Enterprise Admins (519)` |
| **Ticket Lifetime** | 10 giờ (Chính sách AD chuẩn) | **87,600 giờ (~10 năm)** |
| **KDC Event Log** | Có sự kiện $AS\text{-}REQ$ | **KHÔNG có sự kiện $AS\text{-}REQ$** |

---

### 4. Các quy tắc phát hiện (Blue Team Detection)
Module `detector` thực hiện phân tích log theo 3 quy tắc:
* **Rule 1 (Missing AS-REQ):** Phát hiện $TGS\text{-}REQ$ từ một IP không hề gửi $AS\text{-}REQ$ trước đó.
* **Rule 2 (Anomalous Lifetime):** Phát hiện vé có thời hạn sống $> 10$ giờ (dấu hiệu rèn vé bằng Impacket).
* **Rule 3 (Privilege Anomaly):** Phát hiện yêu cầu quản trị nhạy cảm (`/api/admin/flag`) xuất phát từ IP khả nghi.

---

### 5. Tại sao phải "Double Reset" krbtgt?
* Active Directory lưu trữ lịch sử mật khẩu gần nhất của `krbtgt` (Current Key & Previous Key) để các dịch vụ không bị đứt gãy tức thì.
* Nếu chỉ reset **1 lần**, vé Golden Ticket rèn từ khóa cũ **vẫn có thể được KDC chấp nhận**.
* Chỉ khi thực hiện **reset lần thứ 2**, khóa cũ mới bị đẩy hoàn toàn ra khỏi lịch sử mật khẩu, lập tức vô hiệu hóa triệt để mọi vé Golden Ticket đã tạo trước đó.

---

## 🚀 Cài đặt & Khởi động

### Yêu cầu tiên quyết:
* Đã cài đặt **Docker** và **Docker Compose** (hoặc Docker Desktop trên Mac/Windows).
* Cổng `8080` trên máy host đang rảnh.

### 1. Khởi động phòng Lab:

**Trên macOS / Linux / WSL2 / Git Bash:**
```bash
make up
# Hoặc: docker compose up -d --build
```

**Trên Windows (PowerShell / Command Prompt):**
```powershell
docker compose up -d --build
```
> *Lưu ý:* Lần khởi động đầu tiên, Samba AD DC mất khoảng 15-25 giây để provision database và export keytab ra volume dùng chung.

### 2. Kiểm tra trạng thái sẵn sàng (Healthcheck):

**Trên macOS / Linux / WSL2:**
```bash
make healthcheck
# Hoặc: ./scripts/healthcheck.sh
```

**Trên Windows (PowerShell):**
```powershell
.\scripts\healthcheck.ps1
```
Khi thấy tất cả các mục báo `[OK]`, hệ thống đã sẵn sàng cho buổi demo!

---

## 🎬 Kịch bản Demo trực tiếp (7 Màn)

### Chạy tự động liên hoàn toàn bộ kịch bản:

* **Trên macOS / Linux / WSL2:**
  ```bash
  make demo-all
  # Hoặc: ./scripts/demo_all.sh
  ```
* **Trên Windows PowerShell:**
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\demo_all.ps1
  ```

---

### Hoặc thực hiện từng màn độc lập:

#### Màn 1: Xác thực Kerberos hợp lệ (Alice)
```bash
# macOS/Linux: make demo-normal
docker compose exec client python demo_normal.py
```
* **Hiện tượng:** Alice đăng nhập, nhận TGT, truy cập `/api/whoami` thành công (Role: User). Khi Alice thử truy cập `/api/admin/flag`, hệ thống trả về **HTTP 403 Forbidden**.

#### Màn 2: Tấn công Golden Ticket (Attacker)
```bash
# macOS/Linux: make demo-attack
docker compose exec attacker python demo_golden_ticket.py
```
* **Hiện tượng:** Attacker dùng bí mật `krbtgt` rèn TGT mạo danh `administrator` với quyền `Domain Admins`. Attacker truy cập `/api/admin/flag` thành công và nhận được Flag quản trị:
  `CSATTT{G0LD3N_T1CK3T_KRBTGT_P0WN3D_2026}`.

#### Màn 3: Phẫu thuật vé Kerberos & PAC Inspector
```bash
# macOS/Linux: make inspect
docker compose exec client python inspect_ticket.py
```
* **Hiện tượng:** Hiển thị bảng so sánh trực quan từng trường dữ liệu giữa vé của Alice và Golden Ticket (User RID 500, Group 512, Lifetime 10 năm).

#### Màn 4: Giám sát & Báo động (Blue Team Detector)
```bash
# macOS/Linux: make detect
docker compose exec client python -m detector.report
```
* **Hiện tượng:** Hệ thống phân tích log và phát ra các cảnh báo `[CRITICAL]` về việc vé xuất hiện không qua $AS\text{-}REQ$ và thời hạn vé vượt quá 10 giờ.

#### Màn 5: Ứng phó sự cố (Double krbtgt Reset)
```bash
# macOS/Linux: make recover
docker compose exec dc /scripts/rotate_krbtgt.sh
```
* **Hiện tượng:** DC thực hiện reset mật khẩu `krbtgt` 2 lần. Thử dùng lại Golden Ticket cũ $\rightarrow$ **Thất bại ngay lập tức (401)**. Alice đăng nhập lại $\rightarrow$ **Thành công bình thường**.

#### Reset toàn bộ Lab về trạng thái sạch ban đầu:
```bash
# macOS/Linux: make clean hoặc ./scripts/reset.sh
# Windows PowerShell: .\scripts\reset.ps1
```

---

## 📂 Cấu trúc mã nguồn

```text
ce01-lab-csattt-kerberos/
├── .env.example               # Cấu hình biến môi trường mẫu
├── .gitattributes             # Chuẩn hóa ngắt dòng LF cho Windows
├── docker-compose.yml         # Khởi tạo 4 container và mạng cô lập
├── Makefile                   # Gom lệnh demo 1-click
├── README.md                  # Tài liệu hướng dẫn này
├── TECHNICAL_SPECIFICATION.md # Đặc tả kỹ thuật chi tiết
│
├── dc/                        # Samba 4 Active Directory Domain Controller
│   ├── Dockerfile
│   ├── entrypoint.sh          # Quản lý khởi động Samba DC
│   ├── provision.sh           # Tạo domain, user, SPN, export keytab
│   ├── export_domain_info.py  # Trích xuất SID và khóa krbtgt
│   ├── rotate_krbtgt.sh       # Script Double Reset krbtgt
│   └── config/krb5.conf       # Cấu hình Kerberos chuẩn
│
├── api/                       # Python FastAPI Service Server
│   ├── Dockerfile
│   ├── entrypoint.sh          # Đợi keytab và khởi động uvicorn
│   ├── requirements.txt
│   └── app/
│       ├── main.py            # Endpoints: /api/whoami, /api/admin/flag, Web Dashboard
│       ├── kerberos_auth.py   # Xác thực GSSAPI / SPNEGO bằng Keytab
│       └── audit_log.py       # Ghi log xác thực ra file dùng chung
│
├── client/                    # Python Client Container (Alice)
│   ├── Dockerfile
│   ├── client.py              # CLI đăng nhập và gọi API
│   ├── demo_normal.py         # Kịch bản demo xác thực chuẩn
│   └── inspect_ticket.py      # Công cụ so sánh phẫu thuật vé & PAC
│
├── attacker/                  # Attacker Simulator Container
│   ├── Dockerfile
│   └── demo_golden_ticket.py  # Script rèn TGT và bypass xác thực
│
├── detector/                  # Giám sát & Phát hiện bất thường
│   ├── parser.py              # Đọc log xác thực
│   ├── rules.py               # 3 quy tắc phát hiện Golden Ticket
│   └── report.py              # Xuất báo cáo điều tra sự cố
│
└── scripts/                   # Shell scripts tiện ích
    ├── healthcheck.sh         # Kiểm tra tính sẵn sàng của phòng lab
    ├── demo_all.sh            # Chạy tự động liên hoàn 5 màn
    └── reset.sh               # Xóa sạch lab đưa về trạng thái nguyên bản
```

---

## 🛠️ Xử lý sự cố thường gặp

1. **Lỗi `\r`: No such file or directory trên Windows:**
   * Nguyên nhân: Git tự động đổi ký tự ngắt dòng LF thành CRLF.
   * Khắc phục: File `.gitattributes` đã được thiết lập `*.sh text eol=lf`. Nếu gặp lỗi, chạy `dos2unix scripts/*.sh dc/*.sh api/*.sh`.

2. **Lỗi `Server not found in Kerberos database`:**
   * Nguyên nhân: Phân giải DNS hoặc FQDN không khớp.
   * Khắc phục: Kiểm tra lại cấu hình DNS trong `docker-compose.yml` (phải trỏ về `172.20.0.10`).

3. **Truy cập Web Dashboard:**
   * Mở trình duyệt trên máy host: `http://localhost:8080`.
   * Trang web tự động refresh mỗi 5 giây, hiển thị sơ đồ các gói tin Kerberos và bảng log xác thực thời gian thực!
