import React, { useState, useEffect, useRef } from 'react';

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const SUGGESTED_QUESTIONS = [
  "Explain my DBMS syllabus Unit 3 Normalization topics.",
  "When is my Java exam, and what reporting time rule applies?",
  "What is the NEC academic calendar schedule for 2026-2027?",
  "I want to speak to a human staff member for a special fee waiver.",
];

const MOTIVATIONAL_QUOTES = [
  {
    quote: "Engineering is the closest thing to magic that exists in the world.",
    author: "Elon Musk"
  },
  {
    quote: "Success is not final, failure is not fatal: It is the courage to continue that counts.",
    author: "Winston Churchill"
  },
  {
    quote: "The mind is not a vessel to be filled, but a fire to be kindled.",
    author: "Plutarch"
  },
  {
    quote: "Scientists investigate that which already is; Engineers create that which has never been.",
    author: "Albert Einstein"
  },
  {
    quote: "Believe you can and you're halfway there.",
    author: "Theodore Roosevelt"
  }
];

export default function App() {
  // Authentication & Role State ('student' | 'admin' | null)
  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem('nec_user');
    return saved ? JSON.parse(saved) : null;
  });

  // Login Modal State
  const [showLoginModal, setShowLoginModal] = useState(!currentUser);
  const [loginMode, setLoginMode] = useState('student_login'); // 'student_login' | 'student_register' | 'admin_login'
  const [loginForm, setLoginForm] = useState({ name: '', email: '', mobile: '', password: '' });
  const [loginError, setLoginError] = useState(null);

  // Tab State ('dashboard' | 'chat' | 'study' | 'contact' | 'my_queries' | 'docs' | 'escalations')
  const [activeTab, setActiveTab] = useState(() => {
    const user = JSON.parse(localStorage.getItem('nec_user') || 'null');
    return user?.role === 'admin' ? 'escalations' : 'dashboard';
  });
  
  // Chat & Memory State
  const [sessionId, setSessionId] = useState('session_nec_' + Math.floor(Math.random() * 10000));
  const [messages, setMessages] = useState([
    {
      sender: 'assistant',
      text: "Welcome to **NEC Campus Copilot AI**! I am your AI assistant for Narasaraopeta Engineering College (Autonomous). Ask me about course syllabi (DBMS, Java, etc.), exam schedules, academic calendar dates, or college guidelines!",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendHealth, setBackendHealth] = useState(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isListeningVoice, setIsListeningVoice] = useState(false);

  // Student Contact Admin Form State
  const [contactForm, setContactForm] = useState({
    name: currentUser?.name || '',
    email: currentUser?.email || '',
    mobile: currentUser?.mobile || '',
    question: ''
  });
  const [contactStatus, setContactStatus] = useState(null);

  // Student Queries & Notifications State
  const [studentTickets, setStudentTickets] = useState([]);
  const [unreadNotifications, setUnreadNotifications] = useState(0);

  // Motivational Quote State
  const [quoteIndex, setQuoteIndex] = useState(0);

  // Study Mode State
  const [studyTopic, setStudyTopic] = useState('Database Management Systems - Unit 3 Normalization');
  const [studyAction, setStudyAction] = useState('explain_simply');
  const [studyResult, setStudyResult] = useState(null);
  const [studyLoading, setStudyLoading] = useState(false);
  const [flashcardFlipped, setFlashcardFlipped] = useState(false);
  const [currentCardIndex, setCurrentCardIndex] = useState(0);

  // Documents & Admin Portal State
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [escalations, setEscalations] = useState([]);
  const [statusFilter, setStatusFilter] = useState('all');
  const [editingTicket, setEditingTicket] = useState(null);
  const [resolutionNote, setResolutionNote] = useState('');
  const [newStatus, setNewStatus] = useState('reviewed');
  const [adminMediaFile, setAdminMediaFile] = useState(null);
  const [adminMediaUrl, setAdminMediaUrl] = useState(null);
  const [adminUploadStatus, setAdminUploadStatus] = useState(null);

  const chatEndRef = useRef(null);

  useEffect(() => {
    checkHealth();

    if (currentUser?.role === 'admin') {
      fetchEscalations();
    } else if (currentUser?.email) {
      fetchStudentTickets();
    }

    const quoteTimer = setInterval(() => {
      setQuoteIndex((prev) => (prev + 1) % MOTIVATIONAL_QUOTES.length);
    }, 5500);

    return () => clearInterval(quoteTimer);
  }, [currentUser]);

  useEffect(() => {
    if (currentUser) {
      setContactForm((prev) => ({
        ...prev,
        name: currentUser.name || prev.name,
        email: currentUser.email || prev.email,
        mobile: currentUser.mobile || prev.mobile,
      }));
      if (currentUser.role === 'student') {
        fetchStudentTickets();
      }
    }
  }, [currentUser]);

  useEffect(() => {
    if (activeTab === 'chat') {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading, activeTab]);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (res.ok) {
        const data = await res.json();
        setBackendHealth(data);
      } else {
        setBackendHealth({ status: 'error' });
      }
    } catch (err) {
      setBackendHealth({ status: 'offline' });
    }
  };

  const fetchEscalations = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/escalations`);
      if (res.ok) {
        const data = await res.json();
        setEscalations(data.tickets || []);
      }
    } catch (err) {
      console.error("Error fetching escalations:", err);
    }
  };

  const fetchStudentTickets = async () => {
    if (!currentUser?.email) return;
    try {
      const res = await fetch(`${API_BASE_URL}/student-tickets?email=${encodeURIComponent(currentUser.email)}`);
      if (res.ok) {
        const data = await res.json();
        setStudentTickets(data.tickets || []);
        setUnreadNotifications(data.unread_notifications || 0);
      }
    } catch (err) {
      console.error("Error fetching student tickets:", err);
    }
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginError(null);

    if (loginMode === 'admin_login') {
      if (loginForm.name.trim() !== 'VST' || loginForm.password.trim() !== '577577') {
        setLoginError("Invalid Admin credentials! Use Name 'VST' and Password '577577'.");
        return;
      }
    }

    try {
      const endpoint = loginMode === 'student_register' ? '/register' : '/login';
      const bodyPayload = loginMode === 'student_register'
        ? { name: loginForm.name, email: loginForm.email, mobile: loginForm.mobile, password: loginForm.password }
        : { name_or_email: loginForm.name || loginForm.email, password: loginForm.password };

      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyPayload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || data.message || "Authentication failed.");
      }

      const userData = data.user;
      setCurrentUser(userData);
      localStorage.setItem('nec_user', JSON.stringify(userData));
      setShowLoginModal(false);
      setLoginForm({ name: '', email: '', mobile: '', password: '' });

      if (userData.role === 'admin') {
        setActiveTab('escalations');
        fetchEscalations();
      } else {
        setActiveTab('my_queries');
        fetchStudentTickets();
      }
    } catch (err) {
      setLoginError(err.message);
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem('nec_user');
    setShowLoginModal(true);
    setActiveTab('dashboard');
  };

  const handleSend = async (questionText = input) => {
    const query = questionText.trim();
    if (!query || loading) return;

    setError(null);
    setInput('');

    const userMessage = {
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: query,
          session_id: sessionId,
          student_name: currentUser?.name || 'Student',
          email: currentUser?.email || 'student@nec.edu',
          mobile: currentUser?.mobile || 'N/A'
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();

      const assistantMessage = {
        sender: 'assistant',
        text: data.answer || "No response received.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      
      if (currentUser?.role === 'admin') fetchEscalations();
      if (currentUser?.role === 'student') fetchStudentTickets();
      checkHealth();
    } catch (err) {
      console.error("Chat API Error:", err);
      setError(err.message || "Failed to reach backend server.");

      const errorMessage = {
        sender: 'assistant',
        text: `⚠️ **Error**: ${err.message}`,
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleContactSubmit = async (e) => {
    e.preventDefault();
    if (!contactForm.question.trim()) return;

    setContactStatus('Submitting query to Admin (VST)...');

    try {
      const res = await fetch(`${API_BASE_URL}/contact-admin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_name: contactForm.name || 'Student',
          email: contactForm.email || 'student@nec.edu',
          mobile: contactForm.mobile || 'N/A',
          question: contactForm.question,
          reason: "Direct Contact Admin Form Submission"
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setContactStatus(`✅ ${data.message} (Ticket ID: ${data.ticket.ticket_id})`);
        setContactForm((prev) => ({ ...prev, question: '' }));
        if (currentUser?.role === 'student') {
          fetchStudentTickets();
          setActiveTab('my_queries');
        }
        checkHealth();
      } else {
        const errData = await res.json();
        setContactStatus(`❌ Error: ${errData.detail || 'Submission failed'}`);
      }
    } catch (err) {
      setContactStatus(`❌ Network error: ${err.message}`);
    }
  };

  const handleAdminMediaUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setAdminMediaFile(file);
    setAdminUploadStatus("Uploading resolution media file...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE_URL}/upload-resolution-media`, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setAdminMediaUrl(data.file_url);
        setAdminUploadStatus(`✅ Attached file: '${file.filename || file.name}'`);
      } else {
        setAdminUploadStatus("❌ Failed to upload media file.");
      }
    } catch (err) {
      setAdminUploadStatus(`❌ Error: ${err.message}`);
    }
  };

  const handleUpdateTicket = async (ticketId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/escalations/${ticketId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: newStatus,
          resolution_notes: resolutionNote,
          media_file: adminMediaUrl
        }),
      });

      if (res.ok) {
        setEditingTicket(null);
        setResolutionNote('');
        setAdminMediaFile(null);
        setAdminMediaUrl(null);
        setAdminUploadStatus(null);
        fetchEscalations();
        checkHealth();
      }
    } catch (err) {
      console.error("Error updating ticket:", err);
    }
  };

  const handleMarkRead = async (ticketId) => {
    try {
      await fetch(`${API_BASE_URL}/mark-ticket-read/${ticketId}`, { method: 'POST' });
      fetchStudentTickets();
    } catch (err) {
      console.error("Error marking ticket read:", err);
    }
  };

  const handleResetSession = async () => {
    try {
      await fetch(`${API_BASE_URL}/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      setMessages([
        {
          sender: 'assistant',
          text: "🔄 **Conversation Memory Cleared!** You are in a fresh session. What academic question or study material can I help you with?",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (err) {
      console.error("Error resetting session:", err);
    }
  };

  const handleStudyModeAction = async (actionType = studyAction, topicText = studyTopic) => {
    if (!topicText.trim()) return;
    setStudyLoading(true);
    setStudyResult(null);
    setFlashcardFlipped(false);
    setCurrentCardIndex(0);

    try {
      const res = await fetch(`${API_BASE_URL}/study-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: actionType, topic: topicText }),
      });

      if (!res.ok) {
        throw new Error("Failed to generate study content.");
      }

      const data = await res.json();
      setStudyResult(data);
    } catch (err) {
      console.error("Study mode error:", err);
      setStudyResult({ status: 'error', content: '⚠️ Failed to generate study content. Please try again.' });
    } finally {
      setStudyLoading(false);
    }
  };

  const startVoiceInput = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Please use Chrome or Edge.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;

    recognition.onstart = () => setIsListeningVoice(true);
    recognition.onend = () => setIsListeningVoice(false);
    recognition.onerror = () => setIsListeningVoice(false);

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
      setIsListeningVoice(false);
    };

    recognition.start();
  };

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;

    const formData = new FormData();
    formData.append('file', uploadFile);
    setUploadStatus('Uploading & Indexing RAG Document...');

    try {
      const res = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setUploadStatus(`✅ Success: Ingested '${data.filename}' into NEC RAG store! (${data.total_rag_chunks} total chunks indexed)`);
        setUploadFile(null);
        checkHealth();
      } else {
        const errData = await res.json();
        setUploadStatus(`❌ Error: ${errData.detail || 'Upload failed'}`);
      }
    } catch (err) {
      setUploadStatus(`❌ Network error: ${err.message}`);
    }
  };

  const speakText = (text) => {
    if ('speechSynthesis' in window) {
      if (isPlayingAudio) {
        window.speechSynthesis.cancel();
        setIsPlayingAudio(false);
        return;
      }
      const cleanText = text.replace(/###/g, '').replace(/\*\*/g, '').replace(/\[.*?\]/g, '');
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      setIsPlayingAudio(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderFormattedText = (text) => {
    return text.split('\n').map((line, idx) => {
      if (line.startsWith('### ')) {
        return <h4 key={idx} className="md-heading">{line.replace('### ', '')}</h4>;
      }
      if (line.startsWith('- **')) {
        const parts = line.split('**: ');
        return (
          <li key={idx} className="md-list-item">
            <strong>{parts[0].replace('- **', '')}:</strong> {parts.slice(1).join('**: ')}
          </li>
        );
      }
      if (line.startsWith('- ')) {
        return <li key={idx} className="md-list-item">{line.replace('- ', '')}</li>;
      }
      if (!line.trim()) {
        return <div key={idx} className="md-spacer" />;
      }
      return <p key={idx} className="md-paragraph">{line}</p>;
    });
  };

  const sampleFlashcards = [
    { front: "What is Normalization?", back: "Process of organizing tables to eliminate data redundancy and anomalies." },
    { front: "Define 3NF (Third Normal Form)", back: "A table in 2NF where no non-prime attribute is transitively dependent on primary key." },
    { front: "Define BCNF (Boyce-Codd Normal Form)", back: "A strict 3NF variant where for every functional dependency X -> Y, X must be a Super Key." },
    { front: "What are ACID Properties?", back: "Atomicity, Consistency, Isolation, and Durability in database transactions." },
  ];

  const filteredTickets = statusFilter === 'all' 
    ? escalations 
    : escalations.filter(t => t.status === statusFilter);

  return (
    <div className="nec-app-layout">
      {/* Login & Registration Modal */}
      {showLoginModal && (
        <div className="modal-backdrop">
          <div className="login-modal-card">
            <div className="modal-header">
              <div className="nec-logo-badge">NEC</div>
              <h3>Campus Copilot AI Portal</h3>
              <p>Narasaraopeta Engineering College (Autonomous)</p>
            </div>

            <div className="login-tab-switcher">
              <button
                className={loginMode === 'student_login' ? 'active' : ''}
                onClick={() => { setLoginMode('student_login'); setLoginError(null); }}
              >
                Student Login
              </button>
              <button
                className={loginMode === 'student_register' ? 'active' : ''}
                onClick={() => { setLoginMode('student_register'); setLoginError(null); }}
              >
                New Student Register
              </button>
              <button
                className={loginMode === 'admin_login' ? 'active' : ''}
                onClick={() => { setLoginMode('admin_login'); setLoginError(null); setLoginForm({ name: 'VST', email: '', mobile: '', password: '' }); }}
              >
                Admin (VST) Login
              </button>
            </div>

            {loginError && <div className="login-error-msg">⚠️ {loginError}</div>}

            <form onSubmit={handleLoginSubmit} className="login-form">
              {loginMode === 'student_register' && (
                <div className="form-group">
                  <label>Full Student Name:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Alice Smith"
                    value={loginForm.name}
                    onChange={(e) => setLoginForm({ ...loginForm, name: e.target.value })}
                  />
                </div>
              )}

              {loginMode === 'admin_login' ? (
                <div className="form-group">
                  <label>Admin Name:</label>
                  <input
                    type="text"
                    required
                    readOnly
                    value="VST"
                  />
                </div>
              ) : (
                <div className="form-group">
                  <label>Email Address:</label>
                  <input
                    type="email"
                    required
                    placeholder="student@nec.edu"
                    value={loginForm.email}
                    onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                  />
                </div>
              )}

              {loginMode === 'student_register' && (
                <div className="form-group">
                  <label>Mobile Number:</label>
                  <input
                    type="tel"
                    required
                    placeholder="9876543210"
                    value={loginForm.mobile}
                    onChange={(e) => setLoginForm({ ...loginForm, mobile: e.target.value })}
                  />
                </div>
              )}

              <div className="form-group">
                <label>Password:</label>
                <input
                  type="password"
                  required
                  placeholder={loginMode === 'admin_login' ? "Enter Admin Password (577577)" : "Enter Password"}
                  value={loginForm.password}
                  onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                />
              </div>

              <button type="submit" className="login-submit-btn">
                {loginMode === 'student_register' ? 'Register Account & Enter ➔' : (loginMode === 'admin_login' ? 'Log in as Admin (VST) ➔' : 'Log in as Student ➔')}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Sidebar Navigation */}
      <aside className="nec-sidebar">
        <div className="sidebar-brand">
          <div className="nec-logo-badge">NEC</div>
          <div>
            <h2>Campus Copilot AI</h2>
            <p className="college-subtext">Narasaraopeta Engineering College</p>
          </div>
        </div>

        <nav className="sidebar-menu">
          <button className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            📊 Dashboard Overview
          </button>
          <button className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>
            💬 Academic Assistant
          </button>
          <button className={`nav-item ${activeTab === 'study' ? 'active' : ''}`} onClick={() => setActiveTab('study')}>
            📚 Interactive Study Hub
          </button>
          <button className={`nav-item ${activeTab === 'contact' ? 'active' : ''}`} onClick={() => setActiveTab('contact')}>
            ✉️ Contact Admin (VST)
          </button>

          {/* Student Specific Tab */}
          {currentUser?.role === 'student' && (
            <button className={`nav-item ${activeTab === 'my_queries' ? 'active' : ''}`} onClick={() => { setActiveTab('my_queries'); fetchStudentTickets(); }}>
              📋 My Queries & Notifications {unreadNotifications > 0 && <span className="notif-pill">{unreadNotifications}</span>}
            </button>
          )}

          <button className={`nav-item ${activeTab === 'docs' ? 'active' : ''}`} onClick={() => setActiveTab('docs')}>
            📄 Knowledge Base ({backendHealth?.rag_chunks_count || 0})
          </button>

          {/* STRICT ROLE ISOLATION: Admin Only Portal */}
          {currentUser?.role === 'admin' && (
            <button className={`nav-item ${activeTab === 'escalations' ? 'active' : ''}`} onClick={() => { setActiveTab('escalations'); fetchEscalations(); }}>
              🎫 Admin Portal (VST) ({backendHealth?.escalation_tickets_count || 0})
            </button>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="disclaimer-note">
            ⚠️ <strong>Unofficial Assistant</strong><br />
            For official regulations visit <a href="https://www.nrtec.in/" target="_blank" rel="noreferrer">nrtec.in</a>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="nec-main-wrapper">
        {/* Top Header */}
        <header className="nec-header">
          <div className="header-info">
            <span className="college-badge">Autonomous Institution • NAAC 'A+' Grade • EAPCET: NSPE</span>
          </div>

          <div className="header-status-area">
            {currentUser && (
              <div className="user-profile-badge">
                <span>{currentUser.role === 'admin' ? '🛡️ Admin:' : '👤 Student:'} <strong>{currentUser.name}</strong></span>
                <button className="logout-btn" onClick={handleLogout}>Logout</button>
              </div>
            )}

            {currentUser?.role === 'student' && unreadNotifications > 0 && (
              <span className="notif-header-badge" onClick={() => { setActiveTab('my_queries'); fetchStudentTickets(); }} title="New Admin Resolution Received!">
                🔔 {unreadNotifications} New Resolution Email Received
              </span>
            )}

            {backendHealth ? (
              <span className={`badge ${backendHealth.status === 'ok' ? 'badge-success' : 'badge-error'}`}>
                ● {backendHealth.status === 'ok' ? `Backend Online (${backendHealth.groq_configured ? 'Groq API' : 'Mock Fallback'})` : 'Backend Error'}
              </span>
            ) : (
              <span className="badge badge-warning">● Connecting...</span>
            )}

            <button className="memory-reset-btn" onClick={handleResetSession} title="Clear Session Memory">
              🔄 Reset Session
            </button>
          </div>
        </header>

        {/* TAB 1: DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div className="tab-pane dashboard-pane">
            <div className="welcome-banner">
              <span className="welcome-pill-badge">✨ AI-POWERED ACADEMIC COPILOT</span>
              <h2>Welcome to NEC Campus Copilot AI! 👋</h2>
              <p>Your intelligent academic support system for Narasaraopeta Engineering College (Autonomous). Query course syllabi, exam schedules, academic guidelines, or launch Study Mode tools.</p>
            </div>

            <div className="stats-cards-grid">
              <div className="stat-card">
                <span className="stat-icon">📄</span>
                <div>
                  <h4>RAG Document Chunks</h4>
                  <p className="stat-num">{backendHealth?.rag_chunks_count || 0}</p>
                  <span className="stat-sub">Indexed from NEC documents</span>
                </div>
              </div>

              <div className="stat-card">
                <span className="stat-icon">🎫</span>
                <div>
                  <h4>Real Escalations & Queries</h4>
                  <p className="stat-num">{backendHealth?.escalation_tickets_count || 0}</p>
                  <span className="stat-sub">Stored in SQLite DB</span>
                </div>
              </div>

              <div className="stat-card">
                <span className="stat-icon">🤖</span>
                <div>
                  <h4>AI Engine</h4>
                  <p className="stat-num">{backendHealth?.groq_model || 'Groq'}</p>
                  <span className="stat-sub">Multi-turn Tool Calling</span>
                </div>
              </div>
            </div>

            {/* Slow-Motion Auto-Rotating Quote Box with Vibrant Gradient Text */}
            <div className="quote-banner-container">
              <div className="quote-content-box slow-fade-in" key={quoteIndex}>
                <p className="quote-text-vibrant">"{MOTIVATIONAL_QUOTES[quoteIndex].quote}"</p>
                <p className="quote-author-vibrant">— {MOTIVATIONAL_QUOTES[quoteIndex].author}</p>
              </div>
              <div className="quote-dots">
                {MOTIVATIONAL_QUOTES.map((_, idx) => (
                  <span
                    key={idx}
                    className={`quote-dot ${idx === quoteIndex ? 'active' : ''}`}
                    onClick={() => setQuoteIndex(idx)}
                    title={`Quote ${idx + 1}`}
                  />
                ))}
              </div>
            </div>

            <div className="dashboard-columns">
              <div className="dash-col">
                <h3>🚀 Quick Actions</h3>
                <div className="quick-actions-list">
                  <button onClick={() => { setActiveTab('chat'); handleSend("When is my Java exam?"); }}>
                    📅 Check Java Exam Schedule
                  </button>
                  <button onClick={() => { setActiveTab('chat'); handleSend("Explain my DBMS syllabus Unit 3 Normalization."); }}>
                    📖 Query DBMS Syllabus (CS301)
                  </button>
                  <button onClick={() => { setActiveTab('contact'); }}>
                    ✉️ Submit Direct Query to Admin (VST)
                  </button>
                </div>
              </div>

              <div className="dash-col">
                <h3>🔗 Official NEC Portal Links</h3>
                <ul className="official-links-list">
                  <li>🌐 <a href="https://www.nrtec.in/" target="_blank" rel="noreferrer">NEC Official Website (nrtec.in)</a></li>
                  <li>📅 <a href="https://www.nrtec.in/academic-calendar/" target="_blank" rel="noreferrer">Official Academic Calendar</a></li>
                  <li>📢 <a href="https://www.nrtec.in/notifications/" target="_blank" rel="noreferrer">Examination Notifications & Circulars</a></li>
                  <li>📚 <a href="https://www.nrtec.in/syllabus-2/" target="_blank" rel="noreferrer">Autonomous Regulations (R20 / R23) Syllabi</a></li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: ACADEMIC ASSISTANT CHAT */}
        {activeTab === 'chat' && (
          <main className="tab-pane chat-pane">
            {error && (
              <div className="error-banner">
                <span>{error}</span>
                <button onClick={() => setError(null)}>✕</button>
              </div>
            )}

            <div className="messages-list">
              {messages.map((msg, index) => (
                <div key={index} className={`message-row ${msg.sender}`}>
                  <div className="avatar">{msg.sender === 'user' ? '👤' : '🤖'}</div>
                  <div className={`message-bubble ${msg.sender} ${msg.isError ? 'error-bubble' : ''}`}>
                    <div className="message-header">
                      <span className="sender-name">{msg.sender === 'user' ? (currentUser?.name || 'NEC Student') : 'NEC Copilot AI'}</span>
                      <div className="header-right-tools">
                        {msg.sender === 'assistant' && (
                          <button className="audio-speak-btn" onClick={() => speakText(msg.text)} title="Listen to response">
                            {isPlayingAudio ? '⏹️ Stop' : '🔊 Listen'}
                          </button>
                        )}
                        <span className="timestamp">{msg.timestamp}</span>
                      </div>
                    </div>

                    <div className="message-content">{renderFormattedText(msg.text)}</div>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="message-row assistant">
                  <div className="avatar">🤖</div>
                  <div className="message-bubble assistant loading-bubble">
                    <div className="typing-indicator">
                      <span></span><span></span><span></span>
                    </div>
                    <span className="loading-text">NEC Copilot is retrieving documents and executing tools...</span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div className="examples-container">
              <span className="examples-title">Suggested Q&A / Follow-ups:</span>
              <div className="example-chips">
                {SUGGESTED_QUESTIONS.map((q, idx) => (
                  <button key={idx} className="chip-btn" disabled={loading} onClick={() => handleSend(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>

            <div className="input-container">
              <button
                className={`voice-mic-btn ${isListeningVoice ? 'listening' : ''}`}
                onClick={startVoiceInput}
                title="Speak your question using Voice Input"
                disabled={loading}
              >
                {isListeningVoice ? '🔴 Listening...' : '🎙️ Mic'}
              </button>
              <textarea
                className="chat-textarea"
                placeholder="Ask an academic query, syllabus question, follow-up topic, or request staff escalation..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                rows={2}
              />
              <button className="send-btn" onClick={() => handleSend()} disabled={loading || !input.trim()}>
                {loading ? 'Processing...' : 'Send Query ➔'}
              </button>
            </div>
          </main>
        )}

        {/* TAB 3: INTERACTIVE STUDY HUB */}
        {activeTab === 'study' && (
          <div className="tab-pane study-pane">
            <h2>📚 Interactive Study Mode</h2>
            <p className="tab-desc">Generate grounded study materials, plain-language explanations, real-world practical examples, practice questions, and flashcards.</p>

            <div className="study-controls-card">
              <div className="input-group">
                <label>Study Topic / Concept:</label>
                <input
                  type="text"
                  value={studyTopic}
                  onChange={(e) => setStudyTopic(e.target.value)}
                  placeholder="e.g. Database Normalization 3NF vs BCNF"
                />
              </div>

              <div className="study-buttons-row">
                <button
                  className={`action-btn ${studyAction === 'explain_simply' ? 'active' : ''}`}
                  onClick={() => { setStudyAction('explain_simply'); handleStudyModeAction('explain_simply'); }}
                  disabled={studyLoading}
                >
                  💡 Explain Simply
                </button>
                <button
                  className={`action-btn ${studyAction === 'practical_example' ? 'active' : ''}`}
                  onClick={() => { setStudyAction('practical_example'); handleStudyModeAction('practical_example'); }}
                  disabled={studyLoading}
                >
                  🛠️ Practical Example
                </button>
                <button
                  className={`action-btn ${studyAction === 'practice_questions' ? 'active' : ''}`}
                  onClick={() => { setStudyAction('practice_questions'); handleStudyModeAction('practice_questions'); }}
                  disabled={studyLoading}
                >
                  📝 5 Practice Questions
                </button>
                <button
                  className={`action-btn ${studyAction === 'flashcards' ? 'active' : ''}`}
                  onClick={() => { setStudyAction('flashcards'); handleStudyModeAction('flashcards'); }}
                  disabled={studyLoading}
                >
                  🎴 3D Interactive Flashcards
                </button>
                <button
                  className={`action-btn ${studyAction === 'summarize_notes' ? 'active' : ''}`}
                  onClick={() => { setStudyAction('summarize_notes'); handleStudyModeAction('summarize_notes'); }}
                  disabled={studyLoading}
                >
                  📌 Summarize Notes
                </button>
              </div>
            </div>

            {studyLoading && (
              <div className="study-loading">
                <div className="typing-indicator"><span></span><span></span><span></span></div>
                <span>Generating study content...</span>
              </div>
            )}

            {/* 3D Flashcard Interactive Widget */}
            {studyAction === 'flashcards' && !studyLoading && (
              <div className="flashcard-widget-container">
                <h3>🎴 Interactive 3D Study Flashcards (Click Card to Flip)</h3>
                <div className={`flip-card ${flashcardFlipped ? 'flipped' : ''}`} onClick={() => setFlashcardFlipped(!flashcardFlipped)}>
                  <div className="flip-card-inner">
                    <div className="flip-card-front">
                      <span className="card-badge">QUESTION (Card {currentCardIndex + 1}/4)</span>
                      <p>{sampleFlashcards[currentCardIndex].front}</p>
                      <span className="flip-hint">👆 Click to Flip Answer</span>
                    </div>
                    <div className="flip-card-back">
                      <span className="card-badge back">ANSWER</span>
                      <p>{sampleFlashcards[currentCardIndex].back}</p>
                      <span className="flip-hint">👆 Click to Flip Question</span>
                    </div>
                  </div>
                </div>

                <div className="card-controls">
                  <button onClick={() => { setFlashcardFlipped(false); setCurrentCardIndex((prev) => (prev > 0 ? prev - 1 : sampleFlashcards.length - 1)); }}>
                    ◀ Previous Card
                  </button>
                  <button onClick={() => { setFlashcardFlipped(false); setCurrentCardIndex((prev) => (prev < sampleFlashcards.length - 1 ? prev + 1 : 0)); }}>
                    Next Card ▶
                  </button>
                </div>
              </div>
            )}

            {studyResult && studyAction !== 'flashcards' && (
              <div className="study-result-card">
                <div className="study-result-header">
                  {studyResult.is_practice_label && (
                    <div className="practice-disclaimer-badge">
                      ⚠️ {studyResult.is_practice_label}
                    </div>
                  )}
                </div>

                <div className="study-content">
                  {renderFormattedText(studyResult.content)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: CONTACT ADMIN FORM */}
        {activeTab === 'contact' && (
          <div className="tab-pane contact-pane">
            <h2>✉️ Student Contact Admin Form</h2>
            <p className="tab-desc">Submit your query directly to College Administration (Admin: VST). All submissions are stored in SQLite and reviewed by administrative staff.</p>

            <form onSubmit={handleContactSubmit} className="contact-admin-card">
              <div className="form-row">
                <div className="form-group">
                  <label>Student Name:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Alice Smith"
                    value={contactForm.name}
                    onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>Email Address:</label>
                  <input
                    type="email"
                    required
                    placeholder="student@nec.edu"
                    value={contactForm.email}
                    onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Mobile Number:</label>
                <input
                  type="tel"
                  required
                  placeholder="9876543210"
                  value={contactForm.mobile}
                  onChange={(e) => setContactForm({ ...contactForm, mobile: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Query / Issue Description:</label>
                <textarea
                  required
                  rows={4}
                  placeholder="Describe your query or issue for Admin VST..."
                  value={contactForm.question}
                  onChange={(e) => setContactForm({ ...contactForm, question: e.target.value })}
                />
              </div>

              <button type="submit" className="contact-submit-btn">
                📩 Send Query to Admin VST ➔
              </button>

              {contactStatus && <div className="contact-status-msg">{contactStatus}</div>}
            </form>
          </div>
        )}

        {/* TAB 5: STUDENT MY QUERIES & NOTIFICATIONS TAB */}
        {activeTab === 'my_queries' && (
          <div className="tab-pane student-queries-pane">
            <div className="tab-header-row">
              <h2>📋 My Submitted Queries & Admin Responses</h2>
              <button className="refresh-btn" onClick={fetchStudentTickets}>🔄 Refresh Status</button>
            </div>
            <p className="tab-desc">Track the status of your submitted academic queries and view resolution email messages & media files sent by Admin VST.</p>

            {studentTickets.length === 0 ? (
              <div className="empty-state">
                <p>You have not submitted any queries yet.</p>
                <button className="contact-nav-btn" onClick={() => setActiveTab('contact')}>
                  ✉️ Click Here to Submit a Query to Admin VST
                </button>
              </div>
            ) : (
              <div className="student-tickets-list">
                {studentTickets.map((t) => (
                  <div key={t.id} className={`student-ticket-card status-${t.status} ${t.notified ? 'has-notification' : ''}`}>
                    <div className="ticket-card-header">
                      <div className="header-left">
                        <span className="ticket-id">🎫 Ticket ID: {t.id}</span>
                        {t.notified === 1 && (
                          <span className="new-notif-pill" onClick={() => handleMarkRead(t.id)}>
                            🔔 New Email Resolution Received (Click to Dismiss)
                          </span>
                        )}
                      </div>
                      <span className={`status-badge badge-${t.status}`}>{t.status.toUpperCase()}</span>
                    </div>

                    {/* Progress Stepper */}
                    <div className="stepper-timeline">
                      <span className={`step-dot ${t.status === 'pending' || t.status === 'reviewed' || t.status === 'resolved' ? 'active' : ''}`}>1. Submitted</span>
                      <span className={`step-dot ${t.status === 'reviewed' || t.status === 'resolved' ? 'active' : ''}`}>2. Under Review</span>
                      <span className={`step-dot ${t.status === 'resolved' ? 'active' : ''}`}>3. Resolved</span>
                    </div>

                    <div className="ticket-query-box">
                      <p><strong>Your Submitted Query:</strong> {t.student_question}</p>
                      <span className="ticket-meta">Submitted On: {new Date(t.created_at).toLocaleString()}</span>
                    </div>

                    {/* Received Email Resolution Box from Admin VST */}
                    {(t.resolution_notes || t.media_file) && (
                      <div className="received-email-box">
                        <div className="email-header-bar">
                          <span>📧 <strong>Resolution Email Received from Admin VST</strong></span>
                          {t.email_status && <span className="email-status-sub">{t.email_status}</span>}
                        </div>
                        <div className="email-body">
                          <p><strong>From:</strong> Admin VST (&lt;admin@vst.nec.edu&gt;)</p>
                          <p><strong>To:</strong> {t.email} (&lt;{t.email}&gt;)</p>
                          <div className="email-message-content">
                            <strong>Admin Response Message:</strong>
                            <p className="notes-text">"{t.resolution_notes}"</p>
                          </div>

                          {/* Media File Attachment Link */}
                          {t.media_file && (
                            <div className="media-attachment-box">
                              <span>📎 <strong>Attached Resolution File / Document:</strong></span>
                              <a
                                href={`${API_BASE_URL}${t.media_file}`}
                                target="_blank"
                                rel="noreferrer"
                                className="media-download-link"
                              >
                                📥 View / Download Attachment ({t.media_file.split('/').pop()})
                              </a>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 6: KNOWLEDGE BASE */}
        {activeTab === 'docs' && (
          <div className="tab-pane docs-pane">
            <h2>📄 Official NEC Knowledge Base & RAG Ingestion</h2>
            <p className="tab-desc">Access official NEC academic calendars, syllabus handouts, regulations, and upload custom study documents.</p>

            <form className="upload-box" onSubmit={handleFileUpload}>
              <input type="file" accept=".txt,.pdf,.docx,.doc,.csv" onChange={(e) => setUploadFile(e.target.files[0])} />
              <button type="submit" className="upload-btn" disabled={!uploadFile}>
                📤 Upload & Index Document
              </button>
            </form>

            {uploadStatus && <div className="upload-status-msg">{uploadStatus}</div>}

            <div className="documents-list-card">
              <h3>📚 Ingested NEC Academic Documents</h3>
              <ul className="doc-items">
                <li>
                  <strong>nec_college_info.txt</strong> — Official Profile, NAAC A+ Accreditation, AICTE Approval
                  <br /><a href="https://www.nrtec.in/" target="_blank" rel="noreferrer">Source: https://www.nrtec.in/</a>
                </li>
                <li>
                  <strong>nec_academic_calendar.txt</strong> — Official R20/R23 Semester Timelines, Midterm Dates, Fee Deadlines
                  <br /><a href="https://www.nrtec.in/academic-calendar/" target="_blank" rel="noreferrer">Source: https://www.nrtec.in/academic-calendar/</a>
                </li>
                <li>
                  <strong>nec_syllabi_r20_r23.txt</strong> — CS301 Database Management Systems Syllabus Units 1-5
                  <br /><a href="https://www.nrtec.in/syllabus-2/" target="_blank" rel="noreferrer">Source: https://www.nrtec.in/syllabus-2/</a>
                </li>
                <li>
                  <strong>nec_syllabi_r20_r23_java.txt</strong> — JAVA101 Java Programming & OOP Units 1-5
                  <br /><a href="https://www.nrtec.in/syllabus-2/" target="_blank" rel="noreferrer">Source: https://www.nrtec.in/syllabus-2/</a>
                </li>
              </ul>
            </div>
          </div>
        )}

        {/* TAB 7: ADMIN PORTAL (VST) - STRICTLY ADMIN ONLY */}
        {activeTab === 'escalations' && currentUser?.role === 'admin' && (
          <div className="tab-pane escalations-pane">
            <div className="tab-header-row">
              <h2>🎫 Admin Portal — Real Student Queries (VST)</h2>
              <div className="filter-group">
                <label>Filter Status: </label>
                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                  <option value="all">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="reviewed">Reviewed</option>
                  <option value="resolved">Resolved</option>
                </select>
              </div>
            </div>

            <p className="tab-desc">Logged in as Admin <strong>VST</strong>. All real student queries appear here. Respond with resolution text and attach media files to send directly to student email.</p>

            {filteredTickets.length === 0 ? (
              <div className="empty-state">No student queries found in SQLite database.</div>
            ) : (
              <div className="tickets-grid">
                {filteredTickets.map((t) => (
                  <div key={t.id} className={`ticket-card status-${t.status}`}>
                    <div className="ticket-card-header">
                      <span className="ticket-id">🎫 {t.id}</span>
                      <span className={`status-badge badge-${t.status}`}>{t.status.toUpperCase()}</span>
                    </div>

                    {/* Progress Stepper */}
                    <div className="stepper-timeline">
                      <span className={`step-dot ${t.status === 'pending' || t.status === 'reviewed' || t.status === 'resolved' ? 'active' : ''}`}>1. Submitted</span>
                      <span className={`step-dot ${t.status === 'reviewed' || t.status === 'resolved' ? 'active' : ''}`}>2. Under Review</span>
                      <span className={`step-dot ${t.status === 'resolved' ? 'active' : ''}`}>3. Resolved</span>
                    </div>

                    <div className="ticket-body">
                      <p><strong>Student Name:</strong> {t.student_name}</p>
                      <p><strong>Email:</strong> {t.email}</p>
                      <p><strong>Mobile:</strong> {t.mobile}</p>
                      <p><strong>Query:</strong> {t.student_question}</p>
                      <p><strong>Reason / Type:</strong> {t.reason}</p>
                      <p className="ticket-meta">Created At: {new Date(t.created_at).toLocaleString()}</p>

                      {t.resolution_notes && (
                        <div className="resolution-box">
                          <strong>Admin (VST) Notes:</strong> {t.resolution_notes}
                          {t.email_status && <div className="email-status-tag">📧 {t.email_status}</div>}
                          {t.media_file && (
                            <div className="attachment-tag">
                              📎 Attached File: <a href={`${API_BASE_URL}${t.media_file}`} target="_blank" rel="noreferrer">View File</a>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="ticket-actions">
                      <button className="edit-btn" onClick={() => { setEditingTicket(t.id); setNewStatus(t.status); setResolutionNote(t.resolution_notes || ''); setAdminMediaUrl(t.media_file || null); }}>
                        ✉️ Update & Send Email Response
                      </button>
                    </div>

                    {editingTicket === t.id && (
                      <div className="edit-form">
                        <h4>Send Resolution & Email Response (Admin VST)</h4>
                        
                        <div className="form-group">
                          <label>Update Query Status:</label>
                          <select value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
                            <option value="pending">Pending</option>
                            <option value="reviewed">Reviewed</option>
                            <option value="resolved">Resolved</option>
                          </select>
                        </div>

                        <div className="form-group">
                          <label>Email Message / Resolution Notes for Student ({t.email}):</label>
                          <textarea
                            placeholder="Type resolution email text for student (e.g. 'sent you mail check it once')..."
                            value={resolutionNote}
                            onChange={(e) => setResolutionNote(e.target.value)}
                            rows={3}
                          />
                        </div>

                        <div className="form-group">
                          <label>Attach Media File / Document (PDF, Image, Syllabus):</label>
                          <input type="file" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx" onChange={handleAdminMediaUpload} />
                          {adminUploadStatus && <div className="admin-upload-sub">{adminUploadStatus}</div>}
                        </div>

                        <div className="edit-form-btns">
                          <button className="save-btn" onClick={() => handleUpdateTicket(t.id)}>
                            📩 Dispatch Resolution Email & Attachment ➔
                          </button>
                          <button className="cancel-btn" onClick={() => setEditingTicket(null)}>Cancel</button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
