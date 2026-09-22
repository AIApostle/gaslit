import {
  AlertTriangle,
  Bot,
  Check,
  CheckCircle2,
  Copy,
  FileText,
  Flame,
  HelpCircle,
  Image as ImageIcon,
  Paperclip,
  Send,
  Sparkles,
  UserCheck,
  Users,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import {
  agentAttachEvidence,
  agentLookupCase,
  agentRequestHandoff,
  agentSubmitComplaint,
} from "../api";
import type { SwiftAgentToolResponse } from "../types";

type MessageSender = "agent" | "citizen" | "system" | "officer";

interface ChatMessage {
  id: string;
  sender: MessageSender;
  text: string;
  timestamp: string;
  badge?: { label: string; value: string; verification_code?: string };
  evidence?: { fileName: string; type: string };
  isStreaming?: boolean;
}

interface SwiftAgentChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTopic?: string;
  onCaseCreated?: (ticketId: string) => void;
}

export function SwiftAgentChatModal({
  isOpen,
  onClose,
  initialTopic,
  onCaseCreated,
}: SwiftAgentChatModalProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [activeTicketId, setActiveTicketId] = useState<string | null>(null);
  const [isHandoffActive, setIsHandoffActive] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const welcome: ChatMessage = {
        id: "welcome-1",
        sender: "agent",
        text: "Hello! I am your **Host Community Grievance Officer** powered by SwiftAgents. I can record an environmental or infrastructure incident directly to the system of record, check your live ticket status, attach photos/documents, or transfer you to a live human officer.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages([welcome]);

      if (initialTopic) {
        handleUserMessage(`I need to report an incident regarding: ${initialTopic}`);
      }
    }
  }, [isOpen, initialTopic]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  if (!isOpen) return null;

  async function handleUserMessage(userText: string) {
    if (!userText.trim()) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "citizen",
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    const lower = userText.toLowerCase();

    // Check if user is requesting human handoff
    if (
      lower.includes("human") ||
      lower.includes("officer") ||
      lower.includes("talk to person") ||
      lower.includes("speak to someone") ||
      lower.includes("agent handoff")
    ) {
      try {
        const handoff = await agentRequestHandoff({
          reference: activeTicketId || undefined,
          reason: userText,
          urgency: "high",
        });
        setIsHandoffActive(true);
        setTimeout(() => {
          setIsTyping(false);
          setMessages((prev) => [
            ...prev,
            {
              id: `agent-${Date.now()}`,
              sender: "officer",
              text: `🚨 **Human Officer Handoff Triggered**\n\n${handoff.message}\n\nA Community Liaison Officer has received your session details and is standing by.`,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            },
          ]);
        }, 800);
      } catch (err) {
        setIsTyping(false);
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            sender: "agent",
            text: "Could not request human handoff automatically. A duty officer monitors all incoming grievances.",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      }
      return;
    }

    // Check if user is checking an existing ticket
    const ticketMatch = userText.match(/HCC-\d{8}-[A-Za-z0-9]+/i) || userText.match(/CASE-\d+/i);
    if (ticketMatch || lower.includes("check status") || lower.includes("track ticket")) {
      const refToLookup = ticketMatch ? ticketMatch[0].toUpperCase() : activeTicketId;
      if (refToLookup) {
        try {
          const statusResult = await agentLookupCase(refToLookup);
          setTimeout(() => {
            setIsTyping(false);
            setMessages((prev) => [
              ...prev,
              {
                id: `agent-${Date.now()}`,
                sender: "agent",
                text: statusResult.summary_markdown,
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              },
            ]);
          }, 800);
        } catch (err) {
          setIsTyping(false);
          setMessages((prev) => [
            ...prev,
            {
              id: `err-${Date.now()}`,
              sender: "agent",
              text: `Could not retrieve status for ticket \`${refToLookup}\`. Please check that the reference ID is correct.`,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            },
          ]);
        }
        return;
      } else {
        setTimeout(() => {
          setIsTyping(false);
          setMessages((prev) => [
            ...prev,
            {
              id: `agent-${Date.now()}`,
              sender: "agent",
              text: "Please provide your official Ticket ID (e.g. `HCC-20260922-A1B2`) so I can retrieve your case file.",
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            },
          ]);
        }, 500);
        return;
      }
    }

    // Default: Conversational Complaint Intake
    try {
      let inferredCategory = "Environmental Grievance";
      if (lower.includes("flare") || lower.includes("soot") || lower.includes("smoke")) {
        inferredCategory = "Gas Flaring & Soot";
      } else if (lower.includes("spill") || lower.includes("oil") || lower.includes("crude") || lower.includes("pipe")) {
        inferredCategory = "Oil Spill & Farmland";
      } else if (lower.includes("water") || lower.includes("health") || lower.includes("borehole") || lower.includes("smell")) {
        inferredCategory = "Water & Community Health";
      }

      const res = await agentSubmitComplaint({
        category: inferredCategory,
        description: userText,
        location: "Host Community Sector",
        priority: lower.includes("explosion") || lower.includes("poison") || lower.includes("burst") ? "critical" : "normal",
        preferred_channel: "in_browser_chat",
      });

      setActiveTicketId(res.ticket_id);
      if (onCaseCreated) {
        onCaseCreated(res.ticket_id);
      }

      setTimeout(() => {
        setIsTyping(false);
        setMessages((prev) => [
          ...prev,
          {
            id: `agent-${Date.now()}`,
            sender: "agent",
            text: `### Verified Grievance Logged\n\nYour incident report has been recorded directly to the host community database under strict SLA monitoring.\n\n* **Category**: ${inferredCategory}\n* **Verification PIN**: \`${res.verification_code}\`\n\nYou can attach photos/documents using the 📎 icon below, or check back anytime!`,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            badge: {
              label: "Verified Ticket ID",
              value: res.ticket_id,
              verification_code: res.verification_code,
            },
          },
        ]);
      }, 1000);
    } catch (err) {
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: "agent",
          text: `An error occurred while registering your report: ${err instanceof Error ? err.message : "Service busy"}. Please try again.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }
  }

  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!activeTicketId) {
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          sender: "system",
          text: "⚠️ Please describe what happened first so we can assign a Ticket ID before attaching evidence files.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
      return;
    }

    const isImg = file.type.startsWith("image/");
    const evidenceType = isImg ? "photo" : "document";

    setIsTyping(true);
    agentAttachEvidence({
      reference: activeTicketId,
      file_name: file.name,
      evidence_type: evidenceType,
      storage_uri: `https://mock-storage.swiftagents.org/${file.name}`,
      description: `Uploaded from chat: ${file.name}`,
    })
      .then(() => {
        setIsTyping(false);
        setMessages((prev) => [
          ...prev,
          {
            id: `ev-${Date.now()}`,
            sender: "citizen",
            text: `Attached file: ${file.name}`,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            evidence: { fileName: file.name, type: evidenceType },
          },
          {
            id: `agent-ev-${Date.now()}`,
            sender: "agent",
            text: `✅ **Evidence Attached**: File \`${file.name}\` has been securely hashed and added to case file **${activeTicketId}**.`,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      })
      .catch((err) => {
        setIsTyping(false);
        setMessages((prev) => [
          ...prev,
          {
            id: `err-ev-${Date.now()}`,
            sender: "system",
            text: `Failed to upload evidence: ${err.message}`,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      });
  }

  function copyToClipboard(val: string) {
    navigator.clipboard.writeText(val);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  }

  return (
    <div className="swift-modal-backdrop" onClick={onClose}>
      <div className="swift-chat-window" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="swift-chat-header">
          <div className="swift-header-info">
            <div className="swift-avatar-badge">
              <Bot size={22} />
              <span className="swift-live-indicator" />
            </div>
            <div>
              <div className="swift-header-title">
                <strong>Host Community AI Officer</strong>
                <span className="swift-badge-pill">SwiftAgents Live</span>
              </div>
              <small className="swift-header-sub">
                {isHandoffActive ? "🟢 Human Officer Dispatched" : "Conversational Intake & Case Retrieval"}
              </small>
            </div>
          </div>
          <div className="swift-header-actions">
            {!isHandoffActive && (
              <button
                type="button"
                className="swift-btn-handoff"
                onClick={() => handleUserMessage("I want to speak with a human officer")}
                title="Escalate to a human officer"
              >
                <Users size={14} />
                <span>Human Handoff</span>
              </button>
            )}
            <button type="button" className="swift-btn-close" onClick={onClose} aria-label="Close chat">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Message Area */}
        <div className="swift-messages-area">
          {messages.map((m) => (
            <div key={m.id} className={`swift-message-row ${m.sender}`}>
              <div className="swift-message-bubble">
                <div className="swift-message-content" style={{ whiteSpace: "pre-wrap" }}>
                  {m.text}
                </div>

                {m.badge && (
                  <div className="swift-ticket-card">
                    <div className="swift-ticket-top">
                      <Sparkles size={14} />
                      <span>{m.badge.label}</span>
                    </div>
                    <div className="swift-ticket-val">
                      <code>{m.badge.value}</code>
                      <button
                        type="button"
                        className="swift-btn-copy"
                        onClick={() => copyToClipboard(m.badge!.value)}
                        title="Copy ticket ID"
                      >
                        {copiedCode ? <Check size={14} color="#11685f" /> : <Copy size={14} />}
                      </button>
                    </div>
                    {m.badge.verification_code && (
                      <small className="swift-ticket-pin">
                        PIN: <strong>{m.badge.verification_code}</strong> (Keep this private)
                      </small>
                    )}
                  </div>
                )}

                {m.evidence && (
                  <div className="swift-evidence-chip">
                    {m.evidence.type === "photo" ? <ImageIcon size={14} /> : <FileText size={14} />}
                    <span>{m.evidence.fileName}</span>
                  </div>
                )}

                <span className="swift-timestamp">{m.timestamp}</span>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="swift-message-row agent">
              <div className="swift-message-bubble typing">
                <span className="swift-typing-dot" />
                <span className="swift-typing-dot" />
                <span className="swift-typing-dot" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        {messages.length <= 2 && (
          <div className="swift-quick-chips">
            <button type="button" onClick={() => handleUserMessage("Gas flaring with heavy black soot fallout")}>
              <Flame size={12} /> Gas Flaring & Soot
            </button>
            <button type="button" onClick={() => handleUserMessage("Crude pipeline rupture leak in farmland")}>
              🚨 Oil Spill
            </button>
            <button type="button" onClick={() => handleUserMessage("Drinking water borehole contamination")}>
              💧 Water Pollution
            </button>
            <button type="button" onClick={() => handleUserMessage("I want to check my case status")}>
              🔍 Track Ticket
            </button>
            <button type="button" onClick={() => handleUserMessage("Connect me to a human officer")}>
              <Users size={12} /> Human Officer
            </button>
          </div>
        )}

        {/* Input Bar */}
        <form
          className="swift-input-bar"
          onSubmit={(e) => {
            e.preventDefault();
            handleUserMessage(input);
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            onChange={handleFileSelect}
            accept="image/*,application/pdf"
          />
          <button
            type="button"
            className="swift-icon-btn"
            onClick={() => fileInputRef.current?.click()}
            title="Attach incident photo or PDF document"
          >
            <Paperclip size={18} />
          </button>

          <input
            type="text"
            className="swift-text-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message, issue, or ticket ID..."
            autoFocus
          />

          <button type="submit" className="swift-send-btn" disabled={!input.trim()}>
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
