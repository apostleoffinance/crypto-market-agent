import { useState, useRef, useEffect } from 'react';
import { askAI, resetChat } from '../api/marketDataApi';
import { MessageSquare, X, Send, RotateCcw } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function AskAI() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setInput('');
    setLoading(true);

    try {
      const res = await askAI(question, sessionId);
      setSessionId(res.session_id);
      setMessages((prev) => [...prev, { role: 'assistant', content: res.response }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (sessionId) await resetChat(sessionId);
    setMessages([]);
    setSessionId(undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Floating button when closed
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center justify-center w-14 h-14 rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700 transition-colors"
        title="Ask AI Analyst"
      >
        <MessageSquare size={24} />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[400px] h-[520px] bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50">
        <div className="flex items-center gap-2">
          <MessageSquare size={18} className="text-blue-400" />
          <span className="font-semibold text-white text-sm">AI Market Analyst</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleReset}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
            title="Reset conversation"
          >
            <RotateCcw size={16} />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
            title="Close"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center mt-12 space-y-3">
            <MessageSquare size={32} className="mx-auto text-gray-600" />
            <p className="text-gray-400 text-sm">Ask me anything about the crypto market</p>
            <div className="space-y-2 mt-4">
              {[
                'Top 10 coins at end of Q4 2025',
                'Bitcoin price on 2025-06-30',
                'Compare top 5 coins Q1 vs Q4 2024',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion);
                    inputRef.current?.focus();
                  }}
                  className="block w-full text-left text-xs text-gray-500 hover:text-blue-400 bg-gray-800 hover:bg-gray-800/80 rounded-lg px-3 py-2 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
              msg.role === 'user'
                ? 'ml-auto bg-blue-600 text-white rounded-br-sm'
                : 'mr-auto bg-gray-800 text-gray-100 rounded-bl-sm'
            }`}
          >
            {msg.content}
          </div>
        ))}
        {loading && (
          <div className="mr-auto bg-gray-800 text-gray-400 px-3.5 py-2.5 rounded-2xl rounded-bl-sm text-sm">
            <span className="inline-flex gap-1">
              <span className="animate-bounce">.</span>
              <span className="animate-bounce" style={{ animationDelay: '0.1s' }}>.</span>
              <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>.</span>
            </span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-3 py-3 border-t border-gray-700 bg-gray-800/50">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about market data..."
            className="flex-1 bg-gray-800 text-white text-sm rounded-xl px-4 py-2.5 border border-gray-600 focus:border-blue-500 focus:outline-none placeholder-gray-500"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className={`p-2.5 rounded-xl transition-colors ${
              loading || !input.trim()
                ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700 cursor-pointer'
            }`}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
