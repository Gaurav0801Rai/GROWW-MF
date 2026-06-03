"use client";

import { useState, useEffect, useRef } from "react";

interface Message {
  id: string;
  thread_id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citation_url?: string;
}

interface Thread {
  id: string;
  name: string;
  createdAt: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const HDFC_SCHEMES = [
  "HDFC Mid-Cap Opportunities",
  "HDFC Flexi Cap Fund",
  "HDFC Top 100 Fund",
  "HDFC ELSS Tax Saver",
  "HDFC Sensex ETF 100"
];

export default function Home() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string>("Connecting...");

  // Fetch metadata from backend (crawl date)
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/metadata`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.last_updated) {
            const date = new Date(data.last_updated);
            const options: Intl.DateTimeFormatOptions = { month: "long", year: "numeric" };
            const formatted = date.toLocaleDateString("en-US", options);
            setLastUpdated(formatted);
          } else {
            setLastUpdated("Offline");
          }
        } else {
          setLastUpdated("Offline");
        }
      } catch (e) {
        console.error("Failed to fetch metadata", e);
        setLastUpdated("Offline");
      }
    };
    fetchMetadata();
  }, []);

  const feedRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 1. Initial Load: Initialize Chat 1 and Chat 2, or load from LocalStorage
  useEffect(() => {
    const savedThreads = localStorage.getItem("groww_factor_threads");
    const lastActiveThread = localStorage.getItem("groww_factor_active_thread");

    if (savedThreads) {
      const parsedThreads = JSON.parse(savedThreads) as Thread[];
      setThreads(parsedThreads);

      if (lastActiveThread && parsedThreads.some(t => t.id === lastActiveThread)) {
        setActiveThreadId(lastActiveThread);
        fetchMessages(lastActiveThread);
      } else if (parsedThreads.length > 0) {
        setActiveThreadId(parsedThreads[0].id);
        fetchMessages(parsedThreads[0].id);
      } else {
        initializeDefaultThreads();
      }
    } else {
      initializeDefaultThreads();
    }
  }, []);

  // 2. Auto-scroll to bottom of the message feed when messages change
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  // 3. Initialize Default Chat 1 and Chat 2 Sessions
  const initializeDefaultThreads = async () => {
    setIsLoading(true);
    try {
      // Create first thread on backend
      const res1 = await fetch(`${API_BASE_URL}/threads`, { method: "POST" });
      const data1 = await res1.json();
      
      // Create second thread on backend
      const res2 = await fetch(`${API_BASE_URL}/threads`, { method: "POST" });
      const data2 = await res2.json();

      const thread1: Thread = {
        id: data1.thread_id,
        name: "Chat 1",
        createdAt: new Date(Date.now() - 60000).toISOString()
      };
      const thread2: Thread = {
        id: data2.thread_id,
        name: "Chat 2",
        createdAt: new Date().toISOString()
      };

      const defaultThreads = [thread2, thread1]; // Order by newest first
      setThreads(defaultThreads);
      localStorage.setItem("groww_factor_threads", JSON.stringify(defaultThreads));

      setActiveThreadId(data2.thread_id); // Chat 2 is active by default
      localStorage.setItem("groww_factor_active_thread", data2.thread_id);
      setMessages([]);
    } catch (e) {
      console.error("Failed to initialize default sessions", e);
    } finally {
      setIsLoading(false);
    }
  };

  // 4. Fetch Messages from the API
  const fetchMessages = async (threadId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/threads/${threadId}/messages`);
      if (response.ok) {
        const data = await response.json();
        setMessages(data);
      } else {
        console.error("Failed to fetch messages from server.");
      }
    } catch (error) {
      console.error("Error connecting to server:", error);
    }
  };

  // 5. Create a New Thread Session
  const createNewThread = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/threads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        const data = await response.json();
        const newThreadId = data.thread_id;
        const newThread: Thread = {
          id: newThreadId,
          name: `Chat ${threads.length + 1}`,
          createdAt: new Date().toISOString(),
        };

        const updatedThreads = [newThread, ...threads];
        setThreads(updatedThreads);
        localStorage.setItem("groww_factor_threads", JSON.stringify(updatedThreads));
        
        setActiveThreadId(newThreadId);
        localStorage.setItem("groww_factor_active_thread", newThreadId);
        setMessages([]);
      } else {
        alert("Failed to initialize new conversation thread on backend.");
      }
    } catch (error) {
      console.error("Error creating new thread:", error);
      alert("API server is unreachable.");
    } finally {
      setIsLoading(false);
    }
  };

  // 6. Send User Message
  const handleSendMessage = async (textToSend?: string) => {
    const queryText = textToSend ? textToSend.trim() : input.trim();
    if (!queryText || isLoading) return;

    if (!textToSend) {
      setInput("");
    }

    // Add local user message optimistically
    const tempUserMsg: Message = {
      id: Math.random().toString(),
      thread_id: activeThreadId,
      role: "user",
      content: queryText,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/threads/${activeThreadId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: queryText }),
      });

      if (response.ok) {
        const assistantMsg = await response.json();
        setMessages(prev => {
          return [...prev.filter(m => m.id !== tempUserMsg.id), tempUserMsg, assistantMsg];
        });
      } else {
        console.error("Failed to post message to backend API.");
        setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
        alert("Server failed to respond to query.");
      }
    } catch (error) {
      console.error("Network error:", error);
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
      alert("Network error: Cannot reach the backend API server.");
    } finally {
      setIsLoading(false);
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }
  };

  // 7. Select a Thread
  const handleSelectThread = (threadId: string) => {
    setActiveThreadId(threadId);
    localStorage.setItem("groww_factor_active_thread", threadId);
    fetchMessages(threadId);
  };

  // 8. Custom Regex-Based Markdown and Table Parser
  const formatMessageText = (content: string) => {
    const escapeHtml = (text: string) => {
      return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    };

    const formatInline = (text: string) => {
      let formatted = escapeHtml(text);
      // **bold**
      formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      // `code`
      formatted = formatted.replace(/`(.*?)`/g, "<code>$1</code>");
      // [text](url)
      formatted = formatted.replace(/\[(.*?)\]\((https?:\/\/.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
      return formatted;
    };

    const lines = content.split("\n");
    let inTable = false;
    let tableRows: string[] = [];
    const resultHtml: string[] = [];

    const flushTable = () => {
      if (tableRows.length > 0) {
        resultHtml.push("<table>");
        tableRows.forEach((rowText, idx) => {
          const cols = rowText.split("|").slice(1, -1).map(c => c.trim());
          resultHtml.push("<tr>");
          cols.forEach(col => {
            const tag = idx === 0 ? "th" : "td";
            resultHtml.push(`<${tag}>${formatInline(col)}</${tag}>`);
          });
          resultHtml.push("</tr>");
        });
        resultHtml.push("</table>");
        tableRows = [];
        inTable = false;
      }
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.startsWith("|")) {
        if (line.includes("---") || line.includes("===")) {
          continue;
        }
        inTable = true;
        tableRows.push(line);
      } else {
        if (inTable) {
          flushTable();
        }
        if (line === "") {
          resultHtml.push("<br/>");
        } else {
          resultHtml.push(`<p>${formatInline(line)}</p>`);
        }
      }
    }
    if (inTable) {
      flushTable();
    }

    return resultHtml.join("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFundClick = (fundName: string) => {
    setInput(`What is the latest NAV for ${fundName}?`);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div className="app-container">
      {/* 1. Sidebar Panel */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo-row">
            <img src="/groww_logo.png" alt="Groww" className="sidebar-logo-img" />
            <span className="sidebar-title">GROWW</span>
          </div>
          <div className="sidebar-subtitle">Intelligent helper for HDFC Mutual Fund queries.</div>
        </div>

        <button className="new-chat-btn" onClick={createNewThread} disabled={isLoading}>
          + New Chat
        </button>

        <div className="sidebar-section-title">CHART</div>
        <div className="chat-history">
          {threads.map(thread => (
            <div
              key={thread.id}
              className={`chat-history-item ${activeThreadId === thread.id ? "active" : ""}`}
              onClick={() => handleSelectThread(thread.id)}
            >
              {/* Document Icon SVG */}
              <svg className="chat-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
              <span className="chat-item-name">{thread.name}</span>
            </div>
          ))}
        </div>

        <div className="sidebar-divider"></div>

        <div className="sidebar-section-title">HDFC MUTUAL FUNDS</div>
        <div className="static-funds-list">
          {HDFC_SCHEMES.map(fund => (
            <div
              key={fund}
              className="fund-list-item"
              onClick={() => handleFundClick(fund)}
              title={fund}
            >
              {fund}
            </div>
          ))}
        </div>
      </aside>

      {/* 2. Main Chat Panel */}
      <main className="chat-main">

        {messages.length === 0 ? (
          /* Welcome state overlay */
          <div className="welcome-overlay">
            <h1 className="welcome-title">How can I help you today?</h1>
            <p className="welcome-subtitle">
              I provide strict, compliance-aware factual answers directly from official fund documents.
            </p>

            <div className="examples-grid">
              <div
                className="example-card"
                onClick={() => handleSendMessage("What is the latest NAV for HDFC Mid-Cap Opportunities Fund?")}
              >
                <div className="example-card-icon-container">
                  <div className="example-card-icon"></div>
                </div>
                <div className="example-card-text">
                  What is the latest NAV for HDFC Mid-Cap Opportunities Fund?
                </div>
              </div>
              
              <div
                className="example-card"
                onClick={() => handleSendMessage("What is the expense ratio for HDFC Mid-Cap Opportunities Fund?")}
              >
                <div className="example-card-icon-container">
                  <div className="example-card-icon"></div>
                </div>
                <div className="example-card-text">
                  What is the expense ratio for HDFC Mid-Cap Opportunities Fund?
                </div>
              </div>

              <div
                className="example-card"
                onClick={() => handleSendMessage("What is the asset under management (AUM) of HDFC Mid-Cap Opportunities Fund?")}
              >
                <div className="example-card-icon-container">
                  <div className="example-card-icon"></div>
                </div>
                <div className="example-card-text">
                  What is the asset under management (AUM) of HDFC Mid-Cap Opportunities Fund?
                </div>
              </div>

              <div
                className="example-card"
                onClick={() => handleSendMessage("Who is the fund manager for HDFC Flexi Cap Fund?")}
              >
                <div className="example-card-icon-container">
                  <div className="example-card-icon"></div>
                </div>
                <div className="example-card-text">
                  Who is the fund manager for HDFC Flexi Cap Fund?
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Chat messaging feed */
          <div className="chat-feed" ref={feedRef}>
            {messages.map(msg => (
              <div key={msg.id} className={`message-wrapper ${msg.role}`}>
                <div className="message-role-label">{msg.role === "user" ? "Investor" : "Assistant"}</div>
                <div
                  className="chat-bubble"
                  dangerouslySetInnerHTML={{ __html: formatMessageText(msg.content) }}
                ></div>
              </div>
            ))}

            {isLoading && (
              <div className="message-wrapper assistant">
                <div className="message-role-label">Assistant</div>
                <div className="chat-bubble loading-bubble">
                  <div className="dot-pulse"></div>
                  <div className="dot-pulse"></div>
                  <div className="dot-pulse"></div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Animated Rocket launching upwards every 2-3 seconds */}
        <div className="rocket-container">
          <div className="rocket-svg-wrapper">
            <div className="rocket-trail"></div>
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }}>
              {/* Rocket flame */}
              <path d="M12 17C12 17 10 19 10 21C10 22 11 23 12 23C13 23 14 22 14 21C14 19 12 17 12 17Z" fill="#FFB703" />
              <path d="M12 19C12 19 11 20 11 21C11 21.5 11.5 22 12 22C12.5 22 13 21.5 13 21C13 20 12 19 12 19Z" fill="#FB8500" />
              {/* Left fin */}
              <path d="M9 15C9 15 6 16 6 18C6 19 7 19 8 18.5L9.5 16.5L9 15Z" fill="#E63946" />
              {/* Right fin */}
              <path d="M15 15C15 15 18 16 18 18C18 19 17 19 16 18.5L14.5 16.5L15 15Z" fill="#E63946" />
              {/* Main Rocket Body */}
              <path d="M12 2C8 6 8 13 8 16C8 16.5 8.5 17 9 17H15C15.5 17 16 16.5 16 16C16 13 16 6 12 2Z" fill="#F1FAEE" />
              {/* Red tip nose cone */}
              <path d="M12 2C10.2 3.8 9.5 6 9.2 8H14.8C14.5 6 13.8 3.8 12 2Z" fill="#E63946" />
              {/* Rocket window */}
              <circle cx="12" cy="11" r="2" fill="#457B9D" />
              <circle cx="12" cy="11" r="1.3" fill="#A8DADC" />
              {/* Engine exhaust nozzle */}
              <path d="M10 17H14L13.5 18.5H10.5L10 17Z" fill="#1D3557" />
            </svg>
          </div>
        </div>

        {/* Input Bar Section */}
        <div className="input-section">
          <div className="input-box-container">
            <textarea
              ref={inputRef}
              className="chat-text-input"
              placeholder="Ask about HDFC mutual funds?"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={1}
            />
            <button
              className="send-button"
              onClick={() => handleSendMessage()}
              disabled={isLoading || !input.trim()}
              title="Send message"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" className="send-icon-svg">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </div>
          
          <div className="footer-text-row">
            <span className="footer-disclaimer-accent">Facts-only. No investment advice.</span>
            <div className="footer-bullet-separator"></div>
            <span>Powered by verified sources | Last updated: {lastUpdated}</span>
          </div>
        </div>
      </main>
    </div>
  );
}
