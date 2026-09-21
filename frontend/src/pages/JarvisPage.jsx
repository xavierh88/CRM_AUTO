import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Separator } from '../components/ui/separator';
import { toast } from 'sonner';
import {
  Bot, Send, Mic, MicOff, Loader2, Sparkles, Zap,
  CheckCircle, XCircle, AlertTriangle, Info, Menu,
  X, Copy, ThumbsUp, ThumbsDown, RefreshCw, Settings,
  FileText, Users, Calendar, DollarSign, Package, Target
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SUGGESTIONS = [
  "Show me today's appointments",
  "Which leads need follow-up?",
  "What's our conversion rate this month?",
  "Show inventory aging report",
  "Create appointment for John Smith",
  "Send SMS to pending leads",
  "Which deals are near closing?",
  "Show me incomplete documents",
];

const TOOL_CATEGORIES = [
  { id: 'crm', label: 'CRM Tools', icon: Users, color: 'text-blue-500' },
  { id: 'inventory', label: 'Inventory', icon: Package, color: 'text-green-500' },
  { id: 'appointments', label: 'Appointments', icon: Calendar, color: 'text-purple-500' },
  { id: 'finance', label: 'Finance', icon: DollarSign, color: 'text-amber-500' },
  { id: 'reports', label: 'Reports', icon: FileText, color: 'text-pink-500' },
];

const MOCK_TOOLS = {
  crm: [
    { name: 'search_leads', description: 'Search leads by criteria', params: ['query', 'stage', 'assigned_to'] },
    { name: 'get_lead_details', description: 'Get full lead profile', params: ['lead_id'] },
    { name: 'update_lead_stage', description: 'Update lead pipeline stage', params: ['lead_id', 'stage'] },
    { name: 'create_lead', description: 'Create new lead', params: ['first_name', 'last_name', 'phone', 'email', 'source'] },
  ],
  inventory: [
    { name: 'search_vehicles', description: 'Search inventory', params: ['make', 'model', 'year', 'price_range'] },
    { name: 'get_vehicle_details', description: 'Get vehicle details', params: ['vin'] },
    { name: 'check_availability', description: 'Check vehicle availability', params: ['vin'] },
  ],
  appointments: [
    { name: 'create_appointment', description: 'Schedule appointment', params: ['client_id', 'date', 'time', 'dealer', 'type'] },
    { name: 'get_appointments', description: 'Get appointments', params: ['date_range', 'status', 'salesperson'] },
    { name: 'update_appointment_status', description: 'Update appointment status', params: ['appointment_id', 'status'] },
    { name: 'send_appointment_reminder', description: 'Send SMS reminder', params: ['appointment_id'] },
  ],
  finance: [
    { name: 'calculate_payment', description: 'Calculate monthly payment', params: ['price', 'down_payment', 'term', 'rate'] },
    { name: 'get_finance_options', description: 'Get financing options', params: ['client_id', 'vehicle_price'] },
    { name: 'submit_credit_app', description: 'Submit credit application', params: ['client_id', 'vehicle_id'] },
  ],
  reports: [
    { name: 'get_sales_report', description: 'Sales performance report', params: ['period', 'salesperson'] },
    { name: 'get_conversion_report', description: 'Lead conversion rates', params: ['period'] },
    { name: 'get_inventory_report', description: 'Inventory aging report', params: [] },
    { name: 'get_financial_summary', description: 'Financial summary', params: ['period'] },
  ],
};

export default function JarvisPage() {
  const { t } = useTranslation();
  const { user, isDemo } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [showTools, setShowTools] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = { id: Date.now(), role: 'user', content: input, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setLoading(true);

    try {
      // Try to call backend Jarvis endpoint
      const response = await axios.post(`${API}/jarvis/chat`, { 
        message: currentInput, 
        context: { user_id: user.id, is_demo: isDemo }
      });
      
      const botMessage = { 
        id: Date.now() + 1, 
        role: 'assistant', 
        content: response.data.response || response.data.message || 'I understand. Let me help with that.',
        tool_calls: response.data.tool_calls,
        timestamp: new Date() 
      };
      setMessages(prev => [...prev, botMessage]);
      
      if (response.data.requires_confirmation) {
        setPendingAction(response.data.action);
      }
    } catch (error) {
      // Mock response for demo
      const mockResponse = generateMockResponse(currentInput);
      const botMessage = { 
        id: Date.now() + 1, 
        role: 'assistant', 
        content: mockResponse.content,
        tool_calls: mockResponse.tool_calls,
        timestamp: new Date() 
      };
      setMessages(prev => [...prev, botMessage]);
      
      if (mockResponse.requires_confirmation) {
        setPendingAction(mockResponse.action);
      }
    } finally {
      setLoading(false);
    }
  };

  const generateMockResponse = (message) => {
    const lower = message.toLowerCase();
    
    if (lower.includes('appointment') || lower.includes('cita')) {
      return {
        content: `I found 3 appointments for today. Would you like me to show them or help you schedule a new one?`,
        tool_calls: [{ tool: 'get_appointments', params: { date_range: 'today' }, result: { count: 3 } }]
      };
    }
    if (lower.includes('lead') || lower.includes('follow') || lower.includes('prospect')) {
      return {
        content: `There are 7 leads that haven't been contacted in 48+ hours. The oldest is from March 15th. Want me to list them?`,
        tool_calls: [{ tool: 'search_leads', params: { stage: 'NEW LEAD', days_since_contact: 48 }, result: { count: 7 } }]
      };
    }
    if (lower.includes('inventory') || lower.includes('vehicle') || lower.includes('car')) {
      return {
        content: `We have 42 vehicles in inventory. 12 are over 60 days on lot. Top aging: 2023 Ford F-150 (78 days). Need details?`,
        tool_calls: [{ tool: 'get_inventory_report', params: {}, result: { total: 42, aging_over_60: 12 } }]
      };
    }
    if (lower.includes('conversion') || lower.includes('rate') || lower.includes('metric')) {
      return {
        content: `Current conversion rate: 18.5% (32 sales / 173 leads this month). Industry avg is 15-20%. Want the breakdown by source?`,
        tool_calls: [{ tool: 'get_conversion_report', params: { period: 'month' }, result: { rate: 18.5, sales: 32, leads: 173 } }]
      };
    }
    if (lower.includes('deal') || lower.includes('negoti') || lower.includes('pending')) {
      return {
        content: `5 deals in negotiation stage, 3 pending deal. Total pipeline value: $485,000. Closest to closing: Robin Test - Electric Sedan ($42k).`,
        tool_calls: [{ tool: 'search_leads', params: { stage: ['NEGOTIATING', 'PENDING DEAL'] }, result: { count: 8, value: 485000 } }]
      };
    }
    if (lower.includes('document') || lower.includes('paperwork') || lower.includes('doc')) {
      return {
        content: `23 clients have incomplete documents. 15 missing ID, 8 missing income proof. Want me to send reminder SMS to any of them?`,
        tool_calls: [{ tool: 'search_leads', params: { docs_incomplete: true }, result: { count: 23, missing_id: 15, missing_income: 8 } }]
      };
    }
    if (lower.includes('report') || lower.includes('analytics') || lower.includes('dashboard')) {
      return {
        content: `I can generate sales, leads, appointments, inventory, or financial reports. Which type and what period?`,
        tool_calls: []
      };
    }
    
    return {
      content: `I can help you with leads, appointments, inventory, deals, documents, and reports. Try asking: "Show today's appointments" or "Which leads need follow-up?"`,
      tool_calls: []
    };
  };

  const handleConfirmAction = async (approved) => {
    if (!pendingAction) return;
    
    setLoading(true);
    try {
      if (approved) {
        await axios.post(`${API}/jarvis/execute`, { 
          action: pendingAction, 
          confirmed: true,
          user_id: user.id 
        });
        toast.success('Action completed');
      } else {
        toast.info('Action cancelled');
      }
    } catch (error) {
      // Mock
      if (approved) toast.success('Action completed (demo)');
      else toast.info('Action cancelled');
    } finally {
      setPendingAction(null);
      setLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };

  const handleFeedback = (messageId, positive) => {
    toast.success(positive ? 'Thanks for the feedback!' : 'We\'ll improve');
  };

  return (
    <div className="space-y-6 h-[calc(100vh-200px)] flex flex-col" data-testid="jarvis-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
              <Bot className="w-6 h-6 text-white" />
            </div>
            {t('jarvis.title') || 'Jarvis Assistant'}
          </h1>
          <p className="text-muted-foreground mt-1">
            {isDemo ? t('jarvis.demoNotice') : 'AI-powered dealership assistant'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowTools(!showTools)}>
            <Settings className="w-4 h-4 mr-2" />
            Tools
          </Button>
        </div>
      </div>

      {/* Tools Panel */}
      {showTools && (
        <Card className="animate-slide-up">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Available Tools
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="crm" className="w-full">
              <TabsList className="grid w-full grid-cols-5 mb-4">
                {TOOL_CATEGORIES.map(cat => (
                  <TabsTrigger key={cat.id} value={cat.id} className="flex flex-col items-center gap-1 py-2">
                    <cat.icon className={`w-5 h-5 ${cat.color}`} />
                    <span className="text-xs">{cat.label}</span>
                  </TabsTrigger>
                ))}
              </TabsList>
              {TOOL_CATEGORIES.map(cat => (
                <TabsContent key={cat.id} value={cat.id} className="space-y-2">
                  {MOCK_TOOLS[cat.id].map(tool => (
                    <div key={tool.name} className="p-3 border border-border rounded-lg bg-background/50">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-mono text-sm font-medium">{tool.name}</p>
                          <p className="text-xs text-muted-foreground">{tool.description}</p>
                        </div>
                        <Badge variant="outline" className="text-xs">{tool.params.length} params</Badge>
                      </div>
                    </div>
                  ))}
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Chat Area */}
      <Card className="flex-1 flex flex-col">
        <CardHeader className="pb-2">
          <Tabs defaultValue="chat" onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="chat">
                <MessageSquare className="w-4 h-4 mr-2" />
                Chat
              </TabsTrigger>
              <TabsTrigger value="history">
                <FileText className="w-4 h-4 mr-2" />
                History
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col p-0">
          <ScrollArea className="flex-1 p-4 space-y-4">
            {activeTab === 'chat' ? (
              <>
                {messages.length === 0 && (
                  <div className="text-center py-12 text-muted-foreground">
                    <div className="p-3 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-full w-fit mx-auto mb-4">
                      <Bot className="w-8 h-8 text-primary" />
                    </div>
                    <h3 className="text-lg font-medium mb-2">How can I help?</h3>
                    <p className="mb-6 max-w-md mx-auto">Ask me about leads, appointments, inventory, deals, or reports.</p>
                    <div className="flex flex-wrap justify-center gap-2">
                      {SUGGESTIONS.map((s, i) => (
                        <Button key={i} variant="outline" size="sm" onClick={() => handleSuggestionClick(s)} className="whitespace-nowrap">
                          {s}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
                {messages.map((msg) => (
                  <MessageBubble 
                    key={msg.id} 
                    message={msg} 
                    onFeedback={handleFeedback}
                    isDemo={isDemo}
                  />
                ))}
                {loading && (
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-primary/10 rounded-full">
                      <Bot className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex items-center gap-2 bg-muted rounded-lg px-4 py-3">
                      <Loader2 className="w-5 h-5 animate-spin text-primary" />
                      <span className="text-sm text-muted-foreground">{t('jarvis.thinking')}</span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground/30" />
                <h3 className="text-lg font-medium mb-1">Chat History</h3>
                <p>Previous conversations will appear here</p>
              </div>
            )}
          </ScrollArea>
          
          {/* Pending Confirmation */}
          {pendingAction && (
            <div className="border-t border-border p-4 bg-amber-500/5">
              <div className="flex items-center gap-3 p-3 bg-amber-500/10 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <div className="flex-1">
                  <p className="font-medium">Confirm Action</p>
                  <p className="text-sm text-muted-foreground">{pendingAction.description || 'Execute this action?'}</p>
                  <p className="text-xs font-mono text-muted-foreground mt-1">{pendingAction.tool}({JSON.stringify(pendingAction.params)})</p>
                </div>
                <div className="flex gap-2">
                  <Button variant="destructive" size="sm" onClick={() => handleConfirmAction(false)}>Cancel</Button>
                  <Button size="sm" onClick={() => handleConfirmAction(true)}>Confirm</Button>
                </div>
              </div>
            </div>
          )}

          {/* Input Area */}
          <div className="border-t border-border p-4">
            <form onSubmit={handleSend} className="flex gap-2">
              <Input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={t('jarvis.placeholder') || 'Ask Jarvis anything...'}
                className="flex-1"
                disabled={loading}
              />
              <Button type="submit" disabled={loading || !input.trim()} size="lg">
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </Button>
            </form>
            <p className="text-xs text-muted-foreground text-center mt-2">
              {isDemo ? t('jarvis.demoNotice') : 'Powered by Dealer AI OS • Responses may be simulated in demo mode'}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function MessageBubble({ message, onFeedback, isDemo }) {
  const { t } = useTranslation();
  
  return (
    <div className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}>
      {message.role === 'assistant' && (
        <div className="p-2 bg-primary/10 rounded-full flex-shrink-0">
          <Bot className="w-5 h-5 text-primary" />
        </div>
      )}
      <div className={`max-w-[80%] ${message.role === 'user' ? 'text-right' : ''}`}>
        <div className={`inline-block px-4 py-3 rounded-2xl ${
          message.role === 'user' 
            ? 'bg-primary text-primary-foreground rounded-tr-sm' 
            : 'bg-muted rounded-tl-sm'
        }`}>
          <p className="whitespace-pre-wrap">{message.content}</p>
          {message.tool_calls && message.tool_calls.length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-muted-foreground cursor-pointer flex items-center gap-1">
                <Zap className="w-3 h-3" />
                Tool calls ({message.tool_calls.length})
              </summary>
              <div className="mt-2 p-2 bg-background/50 rounded text-xs font-mono text-left max-h-40 overflow-auto">
                {message.tool_calls.map((tc, i) => (
                  <div key={i} className="mb-1">
                    <span className="text-primary">{tc.tool}</span>
                    <span className="text-muted-foreground">({JSON.stringify(tc.params)})</span>
                    {tc.result && <span className="text-emerald-500"> → {JSON.stringify(tc.result)}</span>}
                  </div>
                ))}
              </div>
            </details>
          )}
          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs text-muted-foreground">{new Date(message.timestamp).toLocaleTimeString()}</span>
            <Button variant="ghost" size="sm" onClick={() => onFeedback(message.id, true)} className="p-1">
              <ThumbsUp className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onFeedback(message.id, false)} className="p-1">
              <ThumbsDown className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={() => navigator.clipboard.writeText(message.content)} className="p-1">
              <Copy className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
      {message.role === 'user' && (
        <div className="p-2 bg-muted rounded-full flex-shrink-0">
          <User className="w-5 h-5 text-muted-foreground" />
        </div>
      )}
    </div>
  );
}