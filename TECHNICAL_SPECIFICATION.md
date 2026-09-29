# Technical Specification: Docker-based Kerberos / Active Directory Lab & Golden Ticket Demonstration

## 1. Mục tiêu và Giới hạn dự án

Xây dựng môi trường phòng thí nghiệm (Lab) hoàn toàn độc lập, nhẹ và portable bằng Docker phục vụ bài tập lớn môn **Cơ sở An toàn Thông tin (CSATTT)** với các mục tiêu:

1. **Hiểu và trực quan hóa kiến trúc Active Directory:** Triển khai Samba AD DC cung cấp đầy đủ KDC, LDAP, Kerberos, DNS trong container.
2. **Minh họa quy trình xác thực Kerberos chuẩn:** Phân tích rõ từng cặp thông điệp:
   * $AS\text{-}REQ$ / $AS\text{-}REP$ (Cấp Ticket Granting Ticket - TGT)
   * $TGS\text{-}REQ$ / $TGS\text{-}REP$ (Cấp Service Ticket - ST)
   * $AP\text{-}REQ$ / $AP\text{-}REP$ (Xác thực với Application Service)
3. **Phát triển Client & Service tích hợp Kerberos:** Xây dựng Python Client và FastAPI Service Server xác thực qua chuẩn GSSAPI/SPNEGO.
4. **Minh họa tấn công Golden Ticket (MITRE ATT&CK T1558.001):**
   * Làm rõ bản chất: Tấn công dựa trên việc sở hữu bí mật mật mã của tài khoản `krbtgt` (NTLM Hash / AES-256 Key) để tự rèn TGT giả mạo có chữ ký hợp lệ.
   * Minh họa cấu trúc vé và PAC (Privilege Attribute Certificate): Mạo danh Administrator (RID 500) hoặc tài khoản ảo, tự gán Group Domain Admins (RID 512), tùy biến thời hạn vé (Lifetime 10 năm).
5. **Giám sát & Phát hiện (Blue Team / Detection):** Nhận diện hành vi bất thường thông qua 3 quy tắc:
   * $TGS\text{-}REQ$ xuất hiện mà không có $AS\text{-}REQ$ trước đó.
   * Thời hạn vé bất thường ($> 10$ giờ).
   * PAC bất thường hoặc tài khoản không tồn tại trong LDAP.
6. **Khắc phục (Remediation / Incident Response):** Thực hiện quy trình chuẩn "Double krbtgt password reset" để thu hồi triệt để toàn bộ vé giả mạo.
7. **Khả năng tương thích đa nền tảng (Cross-platform):** Hoạt động mượt mà trên **macOS (Apple Silicon & Intel)**, **Linux (amd64 & arm64)**, và **Windows (Docker Desktop / WSL2)**.

---

## 2. Kiến trúc tổng thể hệ thống

Hệ thống bao gồm 4 container chạy trong mạng nội bộ Docker:

```text
                             Docker Internal Network: 172.20.0.0/24
                                      Domain: LAB.LOCAL

                             ┌───────────────────────────────┐
                             │       DC / KDC Container      │
                             │         172.20.0.10           │
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
   │    172.20.0.30    │           │    172.20.0.20    │           │    172.20.0.50    │
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

### Yêu cầu mạng & Cách ly:
* Network: `172.20.0.0/24`, dạng isolated bridge network.
* Chỉ expose cổng `8080:8000` (FastAPI) ra máy host để phục vụ demo trình duyệt hoặc dashboard.
* Không expose các cổng nhạy cảm (88, 389, 445, 464) ra ngoài LAN thật.

---

## 3. Cấu hình Domain & Thông số kỹ thuật

| Thông số | Giá trị |
| :--- | :--- |
| **Kerberos Realm** | `LAB.LOCAL` (chữ hoa bắt buộc theo chuẩn Kerberos) |
| **DNS Domain** | `lab.local` |
| **NetBIOS Domain** | `LAB` |
| **Domain Controller Hostname** | `dc.lab.local` (IP: `172.20.0.10`) |
| **API Server Hostname** | `api.lab.local` (IP: `172.20.0.20`) |
| **Client Hostname** | `client.lab.local` (IP: `172.20.0.30`) |
| **Attacker Hostname** | `attacker.lab.local` (IP: `172.20.0.50`) |
| **Kerberos Encryption** | `aes256-cts-hmac-sha1-96`, `rc4-hmac` |

---

## 4. Đặc tả các thành phần (Components Specification)

### 4.1. Domain Controller (`dc`)
* **Base Image:** `debian:12-slim` (Hỗ trợ native đa kiến trúc `arm64` và `amd64`).
* **Dịch vụ:** Samba 4 AD DC (`samba`, `winbind`, `krb5-kdc`).
* **Provisioning:**
  - Khởi tạo domain với cấu hình DNS nội bộ (`--dns-backend=SAMBA_INTERNAL`).
  - Tạo các tài khoản:
    * `alice` (Password: `AliceP@ss123!`, Group: `Domain Users`)
    * `bob` (Password: `BobP@ss123!`, Group: `Domain Users`)
    * `administrator` (Password: `AdminP@ss123!`, Group: `Domain Admins`)
    * `service_api` (Service Account dùng để map SPN `HTTP/api.lab.local`)
  - **Keytab Generation:** Tự động xuất keytab dịch vụ ra shared volume:
    ```bash
    samba-tool domain exportkeytab /shared/api.keytab --principal=HTTP/api.lab.local
    ```
  - **Domain Metadata Export:** Xuất Domain SID và thông tin kiểm thử cần thiết vào `/shared/domain_info.json` để phục vụ lab mô phỏng.

### 4.2. Python API Server (`api`)
* **Công nghệ:** Python 3.11, FastAPI, Uvicorn, GSSAPI/SPNEGO (`pyspnego`).
* **Keytab:** Mount từ volume `/shared/api.keytab`.
* **Endpoints:**
  - `GET /api/health`: Kiểm tra trạng thái service.
  - `GET /api/whoami`: Xác thực qua HTTP Header `Authorization: Negotiate <token>`, trả về:
    * `authenticated`: `true`
    * `principal`: `user@LAB.LOCAL`
    * `spn`: `HTTP/api.lab.local`
    * `auth_method`: `Kerberos/SPNEGO`
    * `pac_info`: RID, Group memberships trích xuất từ vé.
  - `GET /api/admin/flag`: Endpoint nhạy cảm chỉ cho phép user thuộc group `Domain Admins` (RID 512).
  - `GET /api/logs`: Trả về log xác thực phục vụ trực quan hóa.

### 4.3. Python Client (`client`)
* **Công nghệ:** Python 3.11, `pyspnego`, `requests`, `gssapi`.
* **Chức năng:**
  - `client.py login <username> [password]`: Xác thực với KDC, nhận TGT lưu vào ccache (`/tmp/krb5cc_lab`).
  - `client.py whoami`: Gửi request kèm SPNEGO token đến API server.
  - `client.py inspect`: Phân tích vé hiện tại trong ccache.

### 4.4. Attacker Simulator (`attacker`)
* **Công nghệ:** Python 3.11, `impacket` (`impacket-ticketer`).
* **Chức năng:**
  - Giả lập tình huống attacker đã có `krbtgt` secret (AES-256 key hoặc NTLM hash) và Domain SID.
  - `demo_golden_ticket.py`:
    1. Tạo Golden Ticket (TGT giả mạo) mạo danh `administrator` hoặc `fake_boss`.
    2. Tự gán User RID `500` và Groups `512` (Domain Admins), `519` (Enterprise Admins).
    3. Đặt Ticket Lifetime = 10 năm ($87,600$ giờ).
    4. Yêu cầu cấp Service Ticket hoặc gửi trực tiếp vé đến API server để truy cập `/api/admin/flag`.

### 4.5. Ticket & PAC Inspector Tool (`inspect_ticket.py`)
* So sánh trực quan giữa vé thật của Alice và vé giả mạo Golden Ticket dưới dạng bảng màu terminal:
  - Principal name
  - User RID
  - Groups RIDs (PAC)
  - Issue Time & Expiration Time
  - KDC/Server Signatures

### 4.6. Blue Team Detector (`detector`)
* Module phân tích log từ KDC và API Server (`detector/report.py`):
  - **Rule 1 (Missing AS-REQ):** Phát hiện $TGS\text{-}REQ$ được gửi tới KDC mà không hề có $AS\text{-}REQ$ tương ứng từ cùng IP/User.
  - **Rule 2 (Abnormal Lifetime):** Phát hiện vé có thời hạn $> 10$ giờ (dấu hiệu đặc trưng của vé rèn bằng công cụ bên ngoài).
  - **Rule 3 (PAC Privilege Check):** Phát hiện tài khoản có claim quyền Admin nhưng không trùng khớp với bản ghi LDAP.

### 4.7. Remediation (`rotate_krbtgt.sh`)
* Minh họa kỹ thuật chuẩn: **Double krbtgt password reset**:
  1. Reset mật khẩu `krbtgt` lần 1.
  2. Giải thích vì sao AD vẫn lưu Previous Key và Golden Ticket vẫn có thể hoạt động.
  3. Reset mật khẩu `krbtgt` lần 2 (đẩy key cũ ra khỏi lịch sử).
  4. Kiểm chứng: Golden Ticket lập tức bị từ chối (`KRB_AP_ERR_MODIFIED`).
  5. Đăng nhập lại với Alice hợp lệ $\rightarrow$ Thành công.

---

## 5. Kịch bản Demo trực tiếp (5 Màn)

```text
[Màn 1: Kiểm tra trạng thái Lab] (1 phút)
   $ make healthcheck
   -> DC: OK | DNS: OK | KDC: OK | API: OK | Client: OK

[Màn 2: Luồng xác thực Kerberos chuẩn] (2 phút)
   $ make demo-normal
   -> Alice đăng nhập -> KDC cấp TGT -> Client xin Service Ticket -> Gọi /api/whoami
   -> API phản hồi: 200 OK | User: alice@LAB.LOCAL | Role: Regular User

[Màn 3: Rèn & Sử dụng Golden Ticket] (3 phút)
   $ make demo-attack
   -> Rèn Forged TGT: administrator@LAB.LOCAL | Groups: Domain Admins | Lifetime: 10 năm
   -> Chạy inspect so sánh 2 vé (Normal vs Golden)
   -> Gọi API /api/admin/flag thành công mà không cần mật khẩu của Administrator!

[Màn 4: Điều tra & Báo động (Detection)] (2 phút)
   $ make detect
   -> Detector hiển thị [CRITICAL ALERT]:
      - TGS-REQ without AS-REQ detected for administrator!
      - Anomalous ticket lifetime: 87600 hours!

[Màn 5: Ứng phó sự cố (Remediation)] (2 phút)
   $ make recover
   -> Thực hiện Double krbtgt reset trên Samba DC
   -> Thử lại Golden Ticket: THẤT BẠI (Invalid Ticket)
   -> Alice đăng nhập lại: THÀNH CÔNG
```

---

## 6. Cấu trúc thư mục mã nguồn

```text
ce01-lab-csattt-kerberos/
├── .env.example
├── .gitattributes
├── Makefile                       # Tự động hóa toàn bộ thao tác demo
├── README.md                      # Hướng dẫn chi tiết lý thuyết và thực hành
├── TECHNICAL_SPECIFICATION.md     # Bản đặc tả kỹ thuật này
├── docker-compose.yml             # Định nghĩa 4 dịch vụ và shared volumes
│
├── dc/                            # Samba 4 AD DC
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── provision.sh
│   ├── rotate_krbtgt.sh
│   └── config/
│       ├── krb5.conf
│       └── smb.conf.template
│
├── api/                           # FastAPI Kerberos Service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── kerberos_auth.py
│       └── audit_log.py
│
├── client/                        # Python Client
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── client.py
│   ├── demo_normal.py
│   └── inspect_ticket.py          # So sánh phẫu thuật vé & PAC
│
├── attacker/                      # Attacker Simulator
│   ├── Dockerfile
│   ├── requirements.txt
│   └── demo_golden_ticket.py      # Tự động rèn vé và bypass xác thực
│
├── detector/                      # Giám sát & Phát hiện
│   ├── parser.py
│   ├── rules.py
│   └── report.py
│
└── scripts/                       # Shell scripts tiện ích
    ├── healthcheck.sh
    ├── demo_all.sh
    └── reset.sh
```

---

## 7. Yêu cầu tương thích đa nền tảng (Cross-platform)

1. **Kiến trúc CPU:**
   - Mọi Dockerfile sử dụng base image đa kiến trúc (`debian:12-slim`, `python:3.11-slim-bookworm`).
   - Biên dịch và cài đặt thư viện hệ thống (`libkrb5-dev`, `libsasl2-dev`) tương thích hoàn toàn cả `arm64` (Apple Silicon M1/M2/M3/M4) và `amd64` (Intel/AMD).
2. **Ký tự ngắt dòng (CRLF / LF):**
   - File `.gitattributes` cấu hình chuẩn `*.sh text eol=lf` tránh lỗi `\r\n` khi chạy từ Windows sang Docker Linux.
3. **Phân giải DNS:**
   - Thiết lập cấu hình DNS tĩnh và fallback `extra_hosts` trong `docker-compose.yml` để đảm bảo FQDN `dc.lab.local`, `api.lab.local` phân giải chính xác trên cả Docker Desktop for Mac/Windows và Docker Engine on Linux.
4. **Volume Mounting:**
   - Dùng Docker Named Volumes (`keytab-data`, `shared-data`) thay vì bind mounts phụ thuộc đường dẫn tuyệt đối của hệ điều hành host.
