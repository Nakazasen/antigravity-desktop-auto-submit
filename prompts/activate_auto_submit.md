# Prompt Kích Hoạt Chế Độ Tự Động Duyệt Lệnh (Auto-Submit) Cho Antigravity Desktop 2.0

Dưới đây là các prompt mẫu được thiết kế sẵn. Bạn có thể sao chép và dán trực tiếp vào khung chat của bất kỳ AI Coding Agent nào (Antigravity IDE, Claude Code, Cursor, Windsurf, v.v.) để yêu cầu Agent tự động kích hoạt tính năng Auto-Submit cho cửa sổ Antigravity Desktop của bạn.

---

## 1. Prompt Dành Cho AI Agent (Agent-to-Agent Activation Prompt)

> **Mục đích:** Dán prompt này vào khung chat của AI Agent để yêu cầu AI tự động quét cổng DevTools nội bộ và tiêm script tự động bấm nút `Submit ↵`.

```markdown
Hãy kích hoạt chế độ Auto-Submit cho ứng dụng Antigravity Desktop 2.0 trên máy của tôi theo cơ chế sau:

1. Đọc cổng Chrome DevTools Protocol (CDP) đang mở tại đường dẫn:
   `%APPDATA%\Antigravity\DevToolsActivePort` (thường là file 2 dòng, dòng đầu tiên là số port).
2. Gọi HTTP GET tới `http://127.0.0.1:<PORT>/json` để lấy danh sách các trang/tab loại "page" có chứa `webSocketDebuggerUrl`.
3. Kết nối WebSocket vào `webSocketDebuggerUrl` và gửi lệnh `Runtime.evaluate` cùng `Page.addScriptToEvaluateOnNewDocument` đoạn mã JavaScript sau:

```javascript
(() => {
  if (window.__agAutoSubmitActive) return 'already_active';
  window.__agAutoSubmitActive = true;
  console.log('[Antigravity Auto-Submit] Da kich hoat thanh cong.');

  setInterval(() => {
    try {
      const buttons = Array.from(document.querySelectorAll('button'));
      const submitBtn = buttons.find(b => {
        const text = (b.innerText || b.textContent || '').trim().toLowerCase();
        return (text === 'submit' || text.startsWith('submit') || text.includes('submit ↵')) &&
               !b.disabled &&
               b.offsetParent !== null;
      });

      if (submitBtn) {
        submitBtn.focus();
        submitBtn.click();
        console.log('[Antigravity Auto-Submit] Da tu dong click Submit vao luc:', new Date().toLocaleTimeString());
      }
    } catch (e) {
      console.error(e);
    }
  }, 500);

  return 'injected_successfully';
})();
```

4. Chạy tiến trình nền giám sát liên tục hoặc báo cáo lại trạng thái kích hoạt sau khi hoàn tất.
```

---

## 2. Prompt Yêu Cầu AI Khởi Chạy Daemon Từ Repository Này

> **Mục đích:** Nếu bạn đã clone repository này về máy, chỉ cần gửi prompt ngắn gọn này:

```markdown
Hãy kiểm tra và khởi chạy file daemon `scripts/antigravity_auto_submit_daemon.py` trong repository `antigravity-desktop-auto-submit` dưới dạng tiến trình nền (background daemon). Xác nhận rằng daemon đã kết nối thành công tới cổng CDP của Antigravity Desktop và đang tự động duyệt các hộp thoại xin quyền.
```

---

## 3. English Version (For International Agents / Repositories)

```markdown
Please activate the hands-free Auto-Submit mode for the Antigravity Desktop 2.0 app on this machine:

1. Locate the Chrome DevTools Protocol (CDP) port file at `%APPDATA%\Antigravity\DevToolsActivePort`.
2. Parse the active port from the first line and fetch targets from `http://127.0.0.1:<PORT>/json`.
3. Connect to the active "page" target via its `webSocketDebuggerUrl`.
4. Inject a lightweight DOM observer / interval via `Runtime.evaluate` and `Page.addScriptToEvaluateOnNewDocument` to automatically detect and click any visible and enabled `Submit ↵` or `Allow` buttons every 500ms.
5. Report the connection status and confirm that automated approval is operational.
```
