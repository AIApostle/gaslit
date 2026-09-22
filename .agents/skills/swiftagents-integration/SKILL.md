---
name: swiftagents-integration
description: Integration guide for SwiftAgents (swiftagents.org) in web applications. Covers web chat widget mounting, custom trigger buttons, tool/function calling, ticket ID badges, file uploads, and real-time human handoff.
---

# SwiftAgents Integration Skill

This skill documents how to integrate and operate **SwiftAgents** (by Serendpt AI) across frontend and backend.

## 1. Web Chat Widget Embedding

### Script Inclusion
```html
<script
  src="https://widget.swiftagents.org/dist/widget-ui.js"
  data-company-id="YOUR_COMPANY_ID"
  data-api-key="swa_live_xxxxxxxxxxxxxxxx"
  defer
></script>
```

### Programmatic JavaScript API
Available on `window.SwiftAgentWidget`:

```typescript
declare global {
  interface Window {
    SwiftAgentWidget?: {
      mount: (companyId: string, options?: {
        baseUrl?: string;
        apiKey?: string;
        mode?: "widget" | "button";
        trigger?: string;
      }) => void;
      unmount: () => void;
      open: () => void;
      close: () => void;
      toggle: () => void;
      readonly isLoaded: boolean;
    };
  }
}
```

## 2. Custom Triggers

To open the chat from custom UI buttons (e.g. "Report via AI Officer"):
```tsx
const handleOpenAI = () => {
  if (window.SwiftAgentWidget?.isLoaded) {
    window.SwiftAgentWidget.open();
  } else {
    console.warn("SwiftAgent widget still loading...");
  }
};
```

## 3. Tool / Function Calling Contract

### Complaint Intake Tool
* **Endpoint**: `POST /v1/agent/complaints`
* **Header**: `X-Agent-Key: <secret>`
* **Payload**:
  ```json
  {
    "complainant_name": "Jane Doe",
    "contact_value": "+234...",
    "preferred_channel": "in_browser_chat",
    "category": "oil_spill",
    "description": "Oil spill near river",
    "location": "Eleme",
    "occurred_at": "2026-09-22T08:00:00Z"
  }
  ```
* **Response**: Returns `case_reference`, `status_verification_code`, and `message` formatted for SwiftAgents ticket badge.

### Status Lookup Tool
* **Endpoint**: `POST /v1/public/status`
* **Payload**:
  ```json
  {
    "reference": "CASE-2026-001",
    "verification_code": "VERIFY-992"
  }
  ```

## 4. Human Handoff (Realtime Socket)

* Escalated sessions trigger SwiftAgents' realtime socket.
* Internal officers receive notice and can intervene directly in the ongoing thread.
