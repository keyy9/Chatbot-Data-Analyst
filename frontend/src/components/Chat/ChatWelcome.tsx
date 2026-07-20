import React from "react";
import { TrendingUp, DollarSign, Users, Activity } from "lucide-react";
import { useChatStore } from "../../store/chatStore";
import { useSessionStore } from "../../store/sessionStore";
import { useProfileStore } from "../../store/profileStore";
import logoImg from "../../assets/logo.png";

export const ChatWelcome: React.FC = () => {
  const { submitUserQuery } = useChatStore();
  const { activeSessionId } = useSessionStore();
  const { profile } = useProfileStore();

  const suggestions = [
    {
      text: "What is the total revenue from completed orders?",
      desc: "Calculate overall revenue from successful sales",
      icon: <DollarSign className="w-4 h-4 text-teal" />
    },
    {
      text: "Which 5 products generated the most revenue?",
      desc: "Identify top-performing products by sales",
      icon: <TrendingUp className="w-4 h-4 text-accent" />
    },
    {
      text: "How many customers are in each tier?",
      desc: "View customer distribution by tier (Gold, Silver, Bronze)",
      icon: <Users className="w-4 h-4 text-cyan-500" />
    },
    {
      text: "Show the number of orders per status",
      desc: "Analyze order status breakdown (completed, cancelled, refunded)",
      icon: <Activity className="w-4 h-4 text-amber-500" />
    }
  ];

  const handleSuggestionClick = (queryText: string) => {
    if (activeSessionId) {
      submitUserQuery(activeSessionId, queryText);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-2xl mx-auto space-y-6 font-sans select-none animate-fade-in">
      {/* Brand logo large icon */}
      <div className="w-16 h-16 bg-gradient-to-tr from-accent to-teal rounded-2xl flex items-center justify-center shadow-lg animate-bounce">
        <img src={logoImg} alt="Lapis AI Logo" className="w-9 h-9 object-contain invert brightness-0" />
      </div>

      {/* Greeting text */}
      <div className="space-y-2">
        <h2 className="text-3xl font-extrabold text-text">
          Welcome, {profile.name}!
        </h2>
        <p className="text-sm text-text-muted leading-relaxed max-w-lg mx-auto">
          I am your natural language database assistant. Ask me questions about our products, customers, and sales orders, and I will compile safe read-only SQL reports.
        </p>
      </div>

      {/* Suggested prompts grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full pt-4">
        {suggestions.map((sug, idx) => (
          <div
            key={idx}
            onClick={() => handleSuggestionClick(sug.text)}
            className="p-5 bg-surface-2/45 border border-border rounded-2xl hover:border-accent/50 cursor-pointer shadow-sm hover:shadow-md transition-all text-left flex items-start gap-4 group hover:scale-[1.02] duration-200"
          >
            <div className="p-2.5 bg-surface-hover rounded-xl group-hover:bg-accent/10 transition-colors">
              {sug.icon}
            </div>
            <div>
              <h4 className="text-sm font-bold text-text group-hover:text-accent transition-colors leading-snug">
                {sug.text}
              </h4>
              <p className="text-xs text-text-faint mt-1 font-medium leading-relaxed">
                {sug.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
