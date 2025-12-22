import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ScrollArea } from './ui/scroll-area';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { Send, User, Bot, Loader2, Phone, RefreshCw } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function SmsInboxDialog({ open, onOpenChange, client, onMessageSent }) {
  const { t, i18n } = useTranslation();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [unreadCount, setUnreadCount] = useState(0);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const dateLocale = i18n.language === 'es' ? es : undefined;

  useEffect(() => {
    if (open && client?.id) {
      fetchMessages();
      markAsRead();
      // Set up polling for new messages
      const interval = setInterval(fetchMessages, 10000); // Poll every 10 seconds
      return () => clearInterval(interval);
    }
  }, [open, client?.id]);

  useEffect(() => {
    // Scroll to bottom when messages change
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const fetchMessages = async () => {
    if (!client?.id) return;
    
    try {
      const response = await axios.get(`${API}/inbox/${client.id}`);
      setMessages(response.data.messages || []);
      setUnreadCount(response.data.unread_count || 0);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async () => {
    if (!client?.id) return;
    try {
      await axios.post(`${API}/inbox/${client.id}/mark-read`);
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || sending) return;

    setSending(true);
    try {
      const formData = new FormData();
      formData.append('message', newMessage.trim());
      
      const response = await axios.post(`${API}/inbox/${client.id}/send`, formData);
      
      // Add message to list
      if (response.data.conversation) {
        setMessages(prev => [...prev, response.data.conversation]);
      }
      
      setNewMessage('');
      toast.success('SMS enviado');
      
      if (onMessageSent) {
        onMessageSent();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar SMS');
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    try {
      const date = parseISO(timestamp);
      return format(date, "d MMM, HH:mm", { locale: dateLocale });
    } catch {
      return timestamp;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg h-[600px] flex flex-col p-0">
        {/* Header */}
        <DialogHeader className="px-4 py-3 border-b bg-slate-50">
          <DialogTitle className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                <User className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="font-semibold text-slate-900">
                  {client?.first_name} {client?.last_name}
                </p>
                <p className="text-sm text-slate-500 flex items-center gap-1">
                  <Phone className="w-3 h-3" />
                  {client?.phone}
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={fetchMessages} disabled={loading}>
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </DialogTitle>
        </DialogHeader>

        {/* Messages */}
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          {loading && messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400">
              <Bot className="w-12 h-12 mb-2" />
              <p>No hay mensajes aún</p>
              <p className="text-sm">Envía el primer mensaje</p>
            </div>
          ) : (
            <div className="space-y-3">
              {messages.map((msg, index) => (
                <div
                  key={msg.id || index}
                  className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                      msg.direction === 'outbound'
                        ? 'bg-blue-600 text-white rounded-br-md'
                        : 'bg-slate-100 text-slate-900 rounded-bl-md'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap break-words">{msg.message}</p>
                    <div className={`flex items-center gap-2 mt-1 text-xs ${
                      msg.direction === 'outbound' ? 'text-blue-100' : 'text-slate-400'
                    }`}>
                      <span>{formatTimestamp(msg.timestamp)}</span>
                      {msg.direction === 'outbound' && msg.sender_name && (
                        <>
                          <span>•</span>
                          <span>{msg.sender_name}</span>
                        </>
                      )}
                      {msg.status === 'failed' && (
                        <Badge variant="destructive" className="text-xs py-0">Error</Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Input */}
        <form onSubmit={handleSend} className="p-3 border-t bg-white">
          <div className="flex items-center gap-2">
            <Input
              ref={inputRef}
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Escribe tu mensaje..."
              className="flex-1"
              disabled={sending}
              maxLength={1600}
            />
            <Button type="submit" disabled={!newMessage.trim() || sending} className="px-4">
              {sending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
          <p className="text-xs text-slate-400 mt-1 text-right">
            {newMessage.length}/1600 caracteres
          </p>
        </form>
      </DialogContent>
    </Dialog>
  );
}
