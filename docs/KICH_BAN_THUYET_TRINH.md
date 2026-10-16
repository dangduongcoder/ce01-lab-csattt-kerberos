# KỊCH BẢN VÀ TÀI LIỆU HƯỚNG DẪN THUYẾT TRÌNH BẢO VỆ LAB
## Đề tài: Cơ chế Xác thực Kerberos & Kỹ thuật Tấn công Golden Ticket (MITRE ATT&CK T1558.001)
**Môn học:** Cơ sở An toàn Thông tin  
**Môi trường:** Docker Lab (4 Containers: Domain Controller, API Service, Client, Attacker)

---

> [!IMPORTANT]
> **Lưu ý quan trọng cho người thuyết trình:**
> - Tài liệu này được thiết kế để bạn mở riêng trên màn hình máy tính cá nhân hoặc máy tính bảng làm **"phao thuyết trình"**.
> - Màn hình máy chiếu (Projector) chỉ hiển thị cửa sổ **Terminal chạy lệnh** và trình duyệt web tại địa chỉ **`http://localhost:8080`**.
> - Các kịch bản dòng lệnh đã được tối ưu tinh gọn, không hiển thị chữ thừa để đảm bảo tính trực quan, chuyên nghiệp nhất trước hội đồng và cả lớp.

---

## 1. Kế hoạch phân bổ thời gian (Tổng thời gian: 12 - 15 phút)

| Phần | Nội dung chính | Thời lượng | Cửa sổ thao tác |
| :--- | :--- | :--- | :--- |
| **Phần 1** | Giới thiệu mô hình Lab & Tổng quan giao thức Kerberos | 2 phút | Slide / Web Dashboard (`http://localhost:8080`) |
| **Phần 2** | Demo Màn 1 & Màn 2: Xác thực hợp lệ & Kiểm soát phân quyền RBAC | 3 phút | Terminal Client (`demo_normal.py`) |
| **Phần 3** | Demo Màn 3: Tấn công Golden Ticket & Leo thang đặc quyền | 3 phút | Terminal Attacker (`demo_golden_ticket.py`) |
| **Phần 4** | Demo Màn 4 & Màn 5: Phẫu thuật vé Kerberos & Giám sát Blue Team | 3 phút | Terminal Client (`inspect_ticket.py`, `detector.report`) |
| **Phần 5** | Demo Màn 6 & Màn 7: Khắc phục sự cố (Double Reset) & Kết luận | 2 phút | Terminal DC (`rotate_krbtgt.sh`) |
| **Phần 6** | Trả lời câu hỏi phản biện của Giảng viên (Q&A) | 3 - 5 phút | Trực tiếp |

---

## 2. Kịch bản lời thoại chi tiết theo từng bước Demo

### Màn 1: Giới thiệu Kiến trúc & Kiểm tra tính sẵn sàng (Healthcheck)
* **Thao tác:** Chạy lệnh `./scripts/healthcheck.sh` hoặc nhấn `[ENTER]` tại Màn 1 trong `./scripts/demo_all.sh`.
* **Màn hình hiển thị:** Kết quả kiểm tra 4 container đều `[OK]`, phân giải DNS nội bộ `[OK]`, API Service `[OK]`.
* **Lời thoại thuyết trình:**
  > *"Kính thưa thầy cô và các bạn, nhóm chúng em xây dựng một môi trường Lab hoàn toàn độc lập dựa trên Docker để mô phỏng chân thực hệ thống Active Directory doanh nghiệp.*
  >
  > *Hệ thống gồm 4 máy trạm trên dải mạng cô lập 172.20.0.0/24:*
  > 1. *Máy `dc.lab.local`: Đóng vai trò Domain Controller chạy Samba 4 AD DC, cung cấp đầy đủ dịch vụ Kerberos KDC trên cổng 88, LDAP và DNS nội bộ.*
  > 2. *Máy `api.lab.local`: Máy chủ dịch vụ Web FastAPI, được tích hợp cơ chế bảo vệ danh tính Kerberos GSSAPI/SPNEGO với định danh SPN là `HTTP/api.lab.local`.*
  > 3. *Máy `client.lab.local`: Đại diện cho máy người dùng hợp lệ Alice.*
  > 4. *Máy `attacker.lab.local`: Đại diện cho máy kẻ tấn công đã cài đặt sẵn bộ công cụ bảo mật Impacket.*
  >
  > *Đồng thời, nhóm đã xây dựng một Web Dashboard tại địa chỉ `http://localhost:8080` giúp quan sát nhật ký xác thực thời gian thực trong suốt quá trình demo."*

---

### Màn 2: Xác thực Kerberos hợp lệ & Kiểm soát phân quyền RBAC
* **Thao tác:** Chạy `python demo_normal.py` trên container `client`. Nhấn `[ENTER]` qua từng phase.
* **Quan sát:** Mở song song trình duyệt `http://localhost:8080` để thấy nhật ký hiện lên.
* **Lời thoại thuyết trình:**

  * **Tại Phase 1 (AS Exchange):**
    > *"Đầu tiên, người dùng Alice đăng nhập vào miền Active Directory. Kerberos áp dụng nguyên tắc **Zero Password Transmission** — mật khẩu người dùng không bao giờ truyền qua mạng.*
    >
    > *Client gửi gói tin **AS-REQ** kèm nhãn thời gian mã hóa bằng mật khẩu của Alice (`Pre-Authentication`). KDC giải mã thành công, xác minh Alice biết mật khẩu và cấp vé **TGT (Ticket Granting Ticket)**. Điểm cốt lõi: Vé TGT này được mã hóa bằng khóa bí mật của tài khoản `krbtgt`. Vì vậy, không ai ngoài KDC có thể đọc hoặc giả mạo nội dung vé TGT."*

  * **Tại Phase 2 (TGS & AP Exchange):**
    > *"Tiếp theo, Alice muốn truy cập API dịch vụ. Alice gửi TGT lên dịch vụ TGS của KDC (**TGS-REQ**) để xin vé dịch vụ cho `HTTP/api.lab.local`.*
    >
    > *KDC giải mã TGT bằng khóa `krbtgt`, thấy hợp lệ nên tạo vé dịch vụ (**Service Ticket - ST**) được mã hóa bằng khóa bí mật của API (`K_api`).*
    >
    > *Sau đó, Client gửi vé dịch vụ qua tiêu đề HTTP `Authorization: Negotiate <Token>` (**AP-REQ**). Máy chủ API dùng file keytab cục bộ để giải mã vé, xác thực Alice thành công mà **hoàn toàn không cần gửi yêu cầu ngược lại Domain Controller**!"*

  * **Tại Phase 3 (RBAC & PAC Validation):**
    > *"Bây giờ, Alice thử truy cập endpoint bảo mật quản trị `/api/admin/flag`. Máy chủ kiểm tra cấu trúc **PAC (Privilege Attribute Certificate)** nằm bên trong vé Kerberos. Do Alice chỉ thuộc nhóm `Domain Users` (RID 513), máy chủ ngay lập tức từ chối với mã lỗi **HTTP 403 Forbidden**.*
    >
    > *Điều này chứng minh Kerberos kiểm soát phân quyền rất nghiêm ngặt. Để vượt qua rào cản này mà không biết mật khẩu Administrator, kẻ tấn công buộc phải sử dụng kỹ thuật rèn vé giả mạo — Golden Ticket."*

---

### Màn 3: Tấn công Golden Ticket (Rèn vé & Chiếm đoạt quyền Administrator)
* **Thao tác:** Chạy `python demo_golden_ticket.py` trên container `attacker`. Nhấn `[ENTER]` qua từng phase.
* **Quan sát:** Trình duyệt `http://localhost:8080` lập tức cập nhật một dòng màu cam đỏ với Role `ADMIN` cho `administrator@LAB.LOCAL`.
* **Lời thoại thuyết trình:**

  * **Tại Bước 1 (Khai thác bí mật $K_{krbtgt}$):**
    > *"Chúng em xin nhấn mạnh: Tấn công Golden Ticket **không phải là brute-force dò tìm mật khẩu**. Kẻ tấn công không cần biết mật khẩu của tài khoản Administrator.*
    >
    > *Trong kịch bản này, giả định kẻ tấn công trước đó đã xâm nhập được vào hệ thống và trích xuất được: (1) Domain SID và (2) Khóa bí mật AES-256 của tài khoản `krbtgt` (ví dụ thông qua kỹ thuật DCSync hoặc dump bộ nhớ LSASS). Tài khoản `krbtgt` là gốc tin cậy của toàn bộ Realm Kerberos."*

  * **Tại Bước 2 (Rèn vé ngoại tuyến - Offline Forgery):**
    > *"Kẻ tấn công sử dụng công cụ `impacket-ticketer` để tự rèn vé TGT. Quá trình này diễn ra **100% ngoại tuyến trên máy của Attacker**, không hề gửi bất kỳ gói tin nào qua mạng, do đó Domain Controller hoàn toàn không hay biết.*
    >
    > *Attacker tự ý sửa đổi dữ liệu bên trong vé:*
    > - *Mạo danh người dùng: `administrator`.*
    > - *Tự gán User RID: `500` (RID mặc định của Domain Admin).*
    > - *Tự gán nhóm: `512` (Domain Admins) và `519` (Enterprise Admins).*
    > - *Nâng thời hạn vé lên: **10 năm (87,600 giờ)** so với chuẩn 10 giờ của hệ thống.*
    > - *Cuối cùng, dùng chính khóa `krbtgt` đã đánh cắp để ký vé. Về mặt toán học, chữ ký mật mã này khớp tuyệt đối với chữ ký của KDC!"*

  * **Tại Bước 3 (Bypass xác thực & Đoạt cờ bí mật):**
    > *"Attacker nạp vé giả mạo vào môi trường và gửi yêu cầu tới API Server. Vì chữ ký mật mã hợp lệ, API Server tin tưởng tuyệt đối rằng yêu cầu này xuất phát từ Domain Administrator.*
    >
    > *Kết quả: Attacker truy cập thành công `/api/admin/flag`, đoạt được cờ bí mật của hệ thống với mã **HTTP 200 OK** mà không cần bất kỳ mật khẩu nào!"*

---

### Màn 4: Phẫu thuật vé Kerberos & Đối chiếu cấu trúc PAC
* **Thao tác:** Chạy `python inspect_ticket.py` trên container `client`.
* **Lời thoại thuyết trình:**
  > *"Để giúp hội đồng nhìn rõ sự khác biệt bên dưới tầng nhị phân, nhóm đã viết công cụ phẫu thuật vé Kerberos để so sánh giữa vé hợp lệ của Alice và vé Golden Ticket:*
  >
  > 1. *Về Thời hạn hiệu lực (Lifetime): Vé của Alice tuân thủ chính sách Domain là 10.0 giờ, trong khi vé Golden Ticket có thời hạn lên tới 10 năm (87,600 giờ).*
  > 2. *Về Cấu trúc PAC: Vé của Alice chỉ mang RID 1104 thuộc nhóm Domain Users (RID 513). Vé của Attacker mang RID 500 thuộc nhóm Domain Admins (RID 512).*
  > 3. *Về Nhật ký KDC: Vé của Alice có sự kiện AS-REQ hợp lệ ghi nhận tại KDC. Vé của Attacker hoàn toàn không có sự kiện AS-REQ (vé tự sinh từ hư không)."*

---

### Màn 5: Giám sát & Phát hiện bất thường (Blue Team Detection Engine)
* **Thao tác:** Chạy `python -m detector.report` trên container `client`.
* **Lời thoại thuyết trình:**
  > *"Về phía phòng thủ (Blue Team), nhóm đã xây dựng một Detection Engine tự động phân tích nhật ký để phát hiện cuộc tấn công thông qua 2 dấu hiệu bất thường cốt lõi:*
  >
  > 1. *Bất thường chuỗi sự kiện (Sequence Anomaly - Mức CRITICAL): Xuất hiện yêu cầu dịch vụ TGS/AP từ địa chỉ IP của Attacker mà trước đó không hề có yêu cầu AS-REQ xin TGT.*
  > 2. *Bất thường thời hạn vé (Lifetime Anomaly - Mức CRITICAL): Vé có thời hạn sống vượt quá ngưỡng tối đa cho phép của Kerberos Domain Policy.*
  >
  > *Ngay khi phát hiện, hệ thống phát cảnh báo vi phạm kỹ thuật MITRE ATT&CK T1558.001 và kích hoạt quy trình ứng phó sự cố."*

---

### Màn 6 & 7: Ứng phó sự cố (Double krbtgt Reset) & Kiểm chứng
* **Thao tác:** Chạy `/scripts/rotate_krbtgt.sh` trên container `dc`, sau đó kiểm chứng lại quyền truy cập của Attacker và Alice.
* **Lời thoại thuyết trình:**
  > *"Để vô hiệu hóa hoàn toàn vé Golden Ticket, biện pháp duy nhất là **Đổi mật khẩu tài khoản krbtgt HAI LẦN LIÊN TIẾP (Double Reset)**.*
  >
  > *Tại sao phải 2 lần? Vì Active Directory luôn lưu trữ 2 khóa cho tài khoản `krbtgt`: Khóa hiện tại (Current) và Khóa trước đó (Previous/History) để tránh ngắt quãng dịch vụ. Nếu chỉ reset 1 lần, khóa bị lộ sẽ chuyển sang trạng thái Previous và vé giả mạo vẫn hoạt động bình thường! Chỉ khi reset lần thứ 2, khóa bị lộ mới bị thanh trừng vĩnh viễn khỏi Active Directory.*
  >
  > *Kiểm chứng sau khôi phục:*
  > - *Kẻ tấn công dùng lại Golden Ticket cũ: Lập tức bị từ chối truy cập (HTTP 401 Unauthorized) vì API và KDC không thể giải mã vé bằng khóa mới.*
  > - *Người dùng hợp lệ Alice: Chỉ cần xác thực lại một lần nữa là hệ thống cấp khóa mới và hoạt động hoàn toàn bình thường."*

---

## 3. Bộ câu hỏi phản biện thường gặp của Giảng viên & Hướng dẫn trả lời

### Câu 1: Tại sao Kerberos không gửi mật khẩu qua mạng nhưng KDC vẫn xác thực được người dùng?
* **Trả lời:**
  > *"Kerberos sử dụng cơ chế **Pre-Authentication (PA-ENC-TIMESTAMP)** theo chuẩn RFC 4120. Khi người dùng nhập mật khẩu tại Client, client sử dụng thuật toán băm (ví dụ PBKDF2/AES-256) để tạo ra khóa bí mật $K_{user}$. Client lấy nhãn thời gian hiện tại (Timestamp), mã hóa bằng $K_{user}$ rồi gửi lên KDC qua gói tin AS-REQ.*
  >
  > *Tại KDC, do KDC nắm giữ mật khẩu băm của người dùng trong cơ sở dữ liệu Active Directory, KDC dùng khóa tương ứng để giải mã nhãn thời gian. Nếu thời gian giải mã khớp với đồng hồ KDC (chênh lệch dưới 5 phút), KDC kết luận client sở hữu mật khẩu chính xác mà mật khẩu không hề xuất hiện trên đường truyền."*

---

### Câu 2: Cấu trúc PAC (Privilege Attribute Certificate) là gì và tại sao người dùng thông thường không tự sửa đổi được quyền hạn của mình trong vé?
* **Trả lời:**
  > *"PAC là phần mở rộng của Microsoft trong Kerberos, chứa thông tin định danh bảo mật (User SID, Group SIDs) dùng cho việc phân quyền (Authorization) tại các dịch vụ.*
  >
  > *Người dùng thông thường không thể sửa đổi PAC vì toàn bộ PAC được đặt bên trong vé TGT (hoặc Service Ticket), và vé này được mã hóa bằng khóa bí mật của KDC ($K_{krbtgt}$) hoặc của dịch vụ ($K_{service}$). Đồng thời, PAC có hai chữ ký số mật mã đi kèm: Server Signature và KDC Signature. Người dùng không sở hữu khóa bí mật nên nếu cố tình chỉnh sửa dù chỉ 1 bit, chữ ký mật mã sẽ bị sai lệch và vé bị từ chối ngay lập tức."*

---

### Câu 3: Máy chủ API làm thế nào để xác thực được người dùng mà không cần gửi truy vấn ngược lại Domain Controller?
* **Trả lời:**
  > *"Kerberos hoạt động theo mô hình mật mã đối xứng phân tán. Khi Client gửi yêu cầu TGS-REQ lên KDC, KDC đóng gói vé Service Ticket được mã hóa bằng chính khóa bí mật của tài khoản dịch vụ API ($K_{api}$).*
  >
  > *Khóa $K_{api}$ này đã được trích xuất sẵn vào một file gọi là **Keytab** (`/etc/api.keytab`) và lưu cục bộ trên máy chủ API. Khi Client gửi vé trong tiêu đề `Authorization: Negotiate`, máy chủ API chỉ cần dùng file Keytab nội bộ của mình để giải mã vé. Nếu giải mã thành công, danh tính người dùng và cấu trúc PAC được chứng minh là do KDC cấp mà không cần bất kỳ kết nối mạng nào về Domain Controller tại thời điểm đó."*

---

### Câu 4: Phân biệt sự khác nhau bản chất giữa Golden Ticket và Silver Ticket?
* **Trả lời:**

| Đặc điểm so sánh | Golden Ticket (Vé Vàng) | Silver Ticket (Vé Bạc) |
| :--- | :--- | :--- |
| **Bí mật bị lộ** | Khóa của tài khoản `krbtgt` ($K_{krbtgt}$) | Khóa của tài khoản dịch vụ cụ thể ($K_{service}$) |
| **Loại vé giả mạo** | Vé cấp vé (**TGT**) | Vé dịch vụ (**Service Ticket**) |
| **Phạm vi tác động** | **Toàn bộ Domain / Forest** (Truy cập mọi máy tính, mọi dịch vụ) | **Chỉ duy nhất 1 dịch vụ** mà khóa bị lộ (Ví dụ: chỉ API hoặc chỉ MSSQL) |
| **Tương tác với KDC** | Có gửi TGS-REQ lên KDC | Hoàn toàn không liên hệ với KDC |
| **Mức độ nguy hiểm** | Tối cao (Domain Compromise) | Trung bình - Cao (Service Compromise) |

---

### Câu 5: Tại sao sau khi người quản trị đổi mật khẩu tài khoản Administrator, vé Golden Ticket vẫn tiếp tục hoạt động?
* **Trả lời:**
  > *"Bởi vì vé Golden Ticket được ký và mã hóa bằng khóa bí mật của tài khoản `krbtgt`, **hoàn toàn độc lập với mật khẩu của tài khoản Administrator**. Khi một máy chủ dịch vụ nhận vé, nó chỉ kiểm tra xem chữ ký của `krbtgt` có hợp lệ hay không chứ không kiểm tra trạng thái mật khẩu của Administrator trong cơ sở dữ liệu.*
  >
  > *Do đó, dù Administrator đổi mật khẩu 100 lần, chừng nào khóa của `krbtgt` chưa bị thay đổi, vé Golden Ticket vẫn có hiệu lực cho đến hết thời hạn (ví dụ 10 năm)."*

---

### Câu 6: Tại sao bắt buộc phải reset mật khẩu tài khoản `krbtgt` đúng 2 lần liên tiếp?
* **Trả lời:**
  > *"Đây là cơ chế kiến trúc của Active Directory nhằm đảm bảo tính sẵn sàng (Fault Tolerance). Active Directory lưu giữ hai thế hệ khóa cho tài khoản `krbtgt`: khóa hiện tại (`Current`) và khóa liền trước (`Previous`) trong thuộc tính lịch sử mật khẩu.*
  >
  > *Nếu người quản trị chỉ đổi mật khẩu 1 lần, khóa bị lộ sẽ trở thành khóa 'Previous'. Khi KDC nhận được vé giả mạo được ký bằng khóa cũ, KDC vẫn chấp nhận giải mã bằng khóa Previous để tránh làm gián đoạn các vé hợp lệ đang lưu hành.*
  >
  > *Chỉ khi thực hiện **lần reset thứ 2**, khóa mới thứ nhất mới chuyển thành Previous, còn khóa bị lộ ban đầu sẽ bị đẩy ra khỏi bộ nhớ và xóa vĩnh viễn khỏi Active Directory, khiến mọi vé Golden Ticket cũ lập tức bị vô hiệu hóa hoàn toàn."*

---

### Câu 7: Trong thực tế, làm thế nào Blue Team phát hiện được cuộc tấn công Golden Ticket khi attacker không gửi yêu cầu AS-REQ lên KDC?
* **Trả lời:**
  > *"Blue Team phát hiện Golden Ticket thông qua kỹ thuật tương quan nhật ký (SIEM Log Correlation) và phân tích hành vi bất thường (UEBA):*
  > 1. *Giám sát Event ID 4769 (A Kerberos service ticket was requested): Nếu hệ thống ghi nhận Event ID 4769 mà trước đó không hề có Event ID 4768 (A Kerberos authentication ticket (TGT) was requested) từ cùng một địa chỉ IP hoặc trong cùng khung thời gian, đó là dấu hiệu chắc chắn của Golden Ticket.*
  > 2. *Giám sát thời hạn vé: Kiểm tra thuộc tính `Ticket Granting Service (TGS) Request Renewal Time`. Mặc định của Active Directory là 10 giờ (hoặc 7 ngày renew). Nếu xuất hiện vé có thời hạn 10 năm (như cấu hình mặc định của Impacket hay Mimikatz), hệ thống SIEM sẽ kích hoạt cảnh báo lập tức.*
  > 3. *Giám sát thuật toán mã hóa (Encryption Type): Kẻ tấn công thường sử dụng mã hóa RC4 (Type 0x17) để rèn vé vì tính toán nhanh, trong khi môi trường hiện đại dùng AES-256 (Type 0x12). Sự xuất hiện của RC4 trong tài khoản đặc quyền là dấu hiệu cảnh báo cao."*
