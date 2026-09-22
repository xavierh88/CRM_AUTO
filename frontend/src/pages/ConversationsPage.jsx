import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ScrollArea } from '../components/ui/scroll-area';
import { toast } from 'sonner';
import {
  Search, MessageSquare, Send, Phone, Mail, Globe, Bell,
  CheckCircle, Clock, User, MoreHorizontal, ChevronDown,
  ChevronUp, Edit, Trash2, Eye, ExternalLink, Download,
  AlertCircle, CheckCircle2, XCircle, Loader2, LayoutList, LayoutGrid
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CHANNELS = [
  { id: 'sms', label: 'SMS', icon: MessageSquare, color: 'bg-emerald-500/20 text-emerald-500' },
  { id: 'email', label: 'Email', icon: Mail, color: 'bg-primary/20 text-primary' },
  { id: 'facebook', label: 'Facebook', icon: Globe, color: 'bg-blue-500/20 text-blue-500' },
  { id: 'instagram', label: 'Instagram', icon: Globe, color: 'bg-pink-500/20 text-pink-500' },
  { id: 'tiktok', label: 'TikTok', icon: Globe, color: 'bg-slate-500/20 text-slate-500' },
  { id: 'webchat', label: 'Web Chat', icon: MessageSquare, color: 'bg-purple-500/20 text-purple-500' },
  { id: 'whatsapp', label: 'WhatsApp', icon: Phone, color: 'bg-emerald-500/20 text-emerald-500' },
];

export default function ConversationsPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [channelFilter, setChannelFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (channelFilter !== 'all') params.append('channel', channelFilter);
      if (statusFilter === 'unread') params.append('unread', 'true');
      
      if (!isAdmin && !isBDCManager) {
        params.append('salesperson_id', user.id);
      }

      const response = await axios.get(`${API}/inbox/conversations?${params.toString()}`);
      setConversations(response.data);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
      setConversations([
        { id: '1', client_id: 'c1', client_name: 'John Smith', client_phone: '+15551234567', channel: 'sms', last_message: 'Thanks for the info!', last_message_at: new Date().toISOString(), unread_count: 2, status: 'active' },
        { id: '2', client_id: 'c2', client_name: 'Maria Garcia', client_phone: '+15559876543', channel: 'email', last_message: 'When can I test drive?', last_message_at: new Date(Date.now() - 3600000).toISOString(), unread_count: 0, status: 'active' },
        { id: '3', client_id: 'c3', client_name: 'Robert Johnson', client_phone: '+15554567890', channel: 'facebook', last_message: 'Interested in the Honda', last_message_at: new Date(Date.now() - 7200000).toISOString(), unread_count: 1, status: 'active' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [searchTerm, channelFilter, statusFilter, user, isAdmin, isBDCManager]);

  const fetchMessages = async (conversationId) => {
    try {
      const response = await axios.get(`${API}/inbox/${conversationId}`);
      setMessages(response.data);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
      setMessages([
        { id: 'm1', conversation_id: conversationId, direction: 'inbound', body: 'Hi, interested in the Accord', created_at: new Date(Date.now() - 3600000).toISOString(), status: 'read' },
        { id: 'm2', conversation_id: conversationId, direction: 'outbound', body: 'Great! When can you come in?', created_at: new Date(Date.now() - 1800000).toISOString(), status: 'sent' },
        { id: 'm3', conversation_id: conversationId, direction: 'inbound', body: 'Tomorrow at 2pm?', created_at: new Date().toISOString(), status: 'delivered' },
      ]);
    }
  };

  const handleSelect = async (conversation) => {
    setSelectedConversation(conversation);
    await fetchMessages(conversation.id);
    if (conversation.unread_count > 0) {
      try {
        await axios.post(`${API}/inbox/${conversation.id}/mark-read`);
        fetchConversations();
      } catch (e) {}
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedConversation) return;
    
    setSending(true);
    try {
      await axios.post(`${API}/inbox/${selectedConversation.id}/send`, { body: newMessage });
      setNewMessage('');
      fetchMessages(selectedConversation.id);
      toast.success('Message sent');
    } catch (error) {
      toast.error('Failed to send');
    } finally {
      setSending(false);
    }
  };

  const getChannelInfo = (channelId) => {
    return CHANNELS.find(c => c.id === channelId) || { label: channelId, icon: MessageSquare, color: 'bg-muted text-muted-foreground' };
  };

  const renderChannelIcon = (channelId) => {
    const info = getChannelInfo(channelId);
    const Icon = info.icon;
    return <Icon className="w-3.5 h-3.5" />;
  };

  const renderChannelIconLarge = (channelId) => {
    const info = getChannelInfo(channelId);
    const Icon = info.icon;
    return <Icon className="w-5 h-5" />;
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (loading) {
    return (
      <div className="space-y-6" data-testid="conversations-page">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">{t('conversations.title')}</h1>
            <p className="text-muted-foreground mt-1">Loading conversations...</p>
          </div>
        </div>
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input placeholder={t('conversations.search')} disabled className="pl-10" />
              </div>
            </div>
          </CardContent>
        </Card>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-1 flex flex-col">
            <CardContent className="flex-1 p-0">
              <div className="p-2 space-y-1 h-[calc(100vh-300px)] overflow-y-auto">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="p-3 bg-muted/50 rounded-lg animate-pulse">
                    <div className="flex items-center gap-2">
                      <div className="loading-spinner" style={{width: '100px', height: '16px', borderWidth: '2px'}} />
                    </div>
                    <div className="loading-spinner" style={{width: '80px', height: '12px', borderWidth: '2px', marginTop: '4px'}} />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card className="lg:col-span-2 flex flex-col">
            <CardContent className="flex-1 flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <MessageSquare className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
                <h3 className="text-lg font-medium mb-1">Select a conversation</h3>
                <p>Choose a conversation from the list to start messaging</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="conversations-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('conversations.title')}</h1>
          <p className="text-muted-foreground mt-1">
            {conversations.filter(c => c.unread_count > 0).length} unread • {conversations.length} conversations
          </p>
        </div>
      </div>

      {/* Search & Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder={t('conversations.search')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={channelFilter} onValueChange={setChannelFilter}>
              <SelectTrigger className="w-full sm:w-36">
                <SelectValue placeholder="Channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Channels</SelectItem>
                {CHANNELS.map(ch => (
                  <SelectItem key={ch.id} value={ch.id}>{ch.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-36">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="unread">Unread</SelectItem>
                <SelectItem value="active">Active</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Conversations List + Chat View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Conversations List */}
        <Card className="lg:col-span-1 flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">{t('conversations.title')}</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 p-0">
            <ScrollArea className="h-[calc(100vh-300px)]" type="always">
              <div className="p-2 space-y-1">
                {conversations.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground">
                    <MessageSquare className="w-12 h-12 mx-auto mb-3 text-muted-foreground/50" />
                    <p>{t('conversations.noConversations')}</p>
                  </div>
                ) : (
                  conversations.map((conv) => (
                    <Button
                      key={conv.id}
                      variant={selectedConversation?.id === conv.id ? 'default' : 'ghost'}
                      className="w-full justify-start text-left gap-3 p-3 hover:bg-muted/50 transition-colors"
                      onClick={() => handleSelect(conv)}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium truncate text-foreground">{conv.client_name}</span>
                          {conv.unread_count > 0 && (
                            <Badge variant="default" className="text-xs ml-auto">{conv.unread_count}</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <div className={`p-1 rounded ${getChannelInfo(conv.channel).color}`}>
                              {renderChannelIcon(conv.channel)}
                            </div>
                            {getChannelInfo(conv.channel).label}
                          </span>
                          <span>•</span>
                          <span>{new Date(conv.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                        <p className="text-sm text-muted-foreground truncate mt-1">{conv.last_message}</p>
                      </div>
                    </Button>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Chat View */}
        <Card className="lg:col-span-2 flex flex-col">
          {selectedConversation ? (
            <>
              <CardHeader className="pb-2 border-b border-border">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${getChannelInfo(selectedConversation.channel).color}`}>
                    {renderChannelIconLarge(selectedConversation.channel)}
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">{selectedConversation.client_name}</h3>
                    <p className="text-sm text-muted-foreground">{selectedConversation.client_phone}</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 p-0 flex flex-col">
                <ScrollArea className="flex-1" type="always">
                  <div className="p-4 space-y-4">
                    {messages.length === 0 ? (
                      <div className="flex items-center justify-center h-full text-muted-foreground">
                        <p>No messages yet. Start the conversation!</p>
                      </div>
                    ) : (
                      messages.map((msg) => (
                        <div key={msg.id} className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[70%] p-3 rounded-2xl ${msg.direction === 'outbound' ? 'bg-primary text-primary-foreground rounded-tr-sm' : 'bg-muted rounded-tl-sm'}`}>
                            <p className="text-sm">{msg.body}</p>
                            <div className="flex items-center gap-1 mt-1 text-xs opacity-70">
                              <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                              {msg.direction === 'outbound' && (
                                <span>{msg.status === 'read' ? '✓✓' : msg.status === 'delivered' ? '✓' : '⏱'}</span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                    <div ref={messagesEndRef} />
                  </div>
                </ScrollArea>
                
                {/* Message Input */}
                <div className="border-t border-border p-4">
                  <form onSubmit={handleSend} className="flex gap-2">
                    <Input
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Type a message..."
                      className="flex-1"
                      disabled={!selectedConversation}
                    />
                    <Button type="submit" disabled={sending || !newMessage.trim() || !selectedConversation}>
                      {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    </Button>
                  </form>
                </div>
              </CardContent>
            </>
          ) : (
            <CardContent className="flex-1 flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <MessageSquare className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
                <h3 className="text-lg font-medium mb-1">Select a conversation</h3>
                <p>Choose a conversation from the list to start messaging</p>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  );
}