import React, { useState } from "react";
import { X, Sparkles, TrendingUp, Users, ShoppingBag, CreditCard, ChevronRight } from "lucide-react";

interface QuickAnalyticsLibraryProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectQuery: (queryText: string) => void;
}

interface AnalyticsTemplate {
  title: string;
  query: string;
  description: string;
  category: "sales" | "customers" | "orders" | "products";
}

const TEMPLATES: AnalyticsTemplate[] = [
  {
    title: "Total Revenue Overview",
    query: "What is the total revenue from completed orders?",
    description: "Calculate total revenue and order volume for completed transactions",
    category: "sales"
  },
  {
    title: "Top 5 Performing Products",
    query: "Which 5 products generated the most revenue?",
    description: "Identify top products ranked by sales amount",
    category: "sales"
  },
  {
    title: "Average Order Value (AOV)",
    query: "What is the average order amount for completed orders?",
    description: "Measure average spending per completed purchase",
    category: "sales"
  },
  {
    title: "Customer Tier Distribution",
    query: "How many customers are in each tier?",
    description: "Count customers categorized by tier (Gold, Silver, Bronze)",
    category: "customers"
  },
  {
    title: "Top 5 High-Value VIP Customers",
    query: "Who are the top 5 highest spending customers?",
    description: "List customers with highest cumulative purchases",
    category: "customers"
  },
  {
    title: "Geographic Customer Breakdown",
    query: "Show customer count grouped by city",
    description: "Analyze geographic distribution of user base",
    category: "customers"
  },
  {
    title: "Order Status Breakdown",
    query: "Show the number of orders per status",
    description: "Analyze status ratios (completed, pending, cancelled, refunded)",
    category: "orders"
  },
  {
    title: "Payment Method Revenue Share",
    query: "Which payment methods contributed most to revenue?",
    description: "Compare total revenue by payment channel",
    category: "orders"
  },
  {
    title: "Cancelled Orders Inspection",
    query: "List recent cancelled orders with customer names and order amounts",
    description: "Inspect recent order cancellations for operational review",
    category: "orders"
  },
  {
    title: "Sales Volume by Product Category",
    query: "Which category has the highest sales volume?",
    description: "Break down total units sold across product categories",
    category: "products"
  },
  {
    title: "Low Inventory Stock Alert",
    query: "List products with stock count less than 20",
    description: "Identify products requiring inventory replenishment",
    category: "products"
  }
];

export const QuickAnalyticsLibrary: React.FC<QuickAnalyticsLibraryProps> = ({
  isOpen,
  onClose,
  onSelectQuery
}) => {
  const [activeCategory, setActiveCategory] = useState<"all" | "sales" | "customers" | "orders" | "products">("all");

  if (!isOpen) return null;

  const filtered = activeCategory === "all"
    ? TEMPLATES
    : TEMPLATES.filter((t) => t.category === activeCategory);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in font-sans">
      <div className="bg-surface border border-border w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden glass-panel">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border/80 bg-bg-elevated">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-text">Quick Analytics Library</h3>
              <p className="text-xs text-text-muted">1-click preset business queries and insights</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-full text-text-muted hover:text-text hover:bg-surface-hover transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Category Tabs */}
        <div className="flex items-center gap-2 px-5 py-3 border-b border-border/50 bg-surface-2/40 overflow-x-auto scrollbar-none">
          <button
            type="button"
            onClick={() => setActiveCategory("all")}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeCategory === "all" ? "bg-accent text-white shadow-sm" : "text-text-muted hover:text-text hover:bg-surface-hover"
            }`}
          >
            All Templates
          </button>
          <button
            type="button"
            onClick={() => setActiveCategory("sales")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeCategory === "sales" ? "bg-accent text-white shadow-sm" : "text-text-muted hover:text-text hover:bg-surface-hover"
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" /> Sales & Revenue
          </button>
          <button
            type="button"
            onClick={() => setActiveCategory("customers")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeCategory === "customers" ? "bg-accent text-white shadow-sm" : "text-text-muted hover:text-text hover:bg-surface-hover"
            }`}
          >
            <Users className="w-3.5 h-3.5" /> Customers
          </button>
          <button
            type="button"
            onClick={() => setActiveCategory("orders")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeCategory === "orders" ? "bg-accent text-white shadow-sm" : "text-text-muted hover:text-text hover:bg-surface-hover"
            }`}
          >
            <CreditCard className="w-3.5 h-3.5" /> Orders
          </button>
          <button
            type="button"
            onClick={() => setActiveCategory("products")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeCategory === "products" ? "bg-accent text-white shadow-sm" : "text-text-muted hover:text-text hover:bg-surface-hover"
            }`}
          >
            <ShoppingBag className="w-3.5 h-3.5" /> Products
          </button>
        </div>

        {/* Template List */}
        <div className="flex-1 overflow-y-auto p-5 space-y-2.5 scrollbar-thin">
          {filtered.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                onSelectQuery(item.query);
                onClose();
              }}
              className="w-full text-left p-3.5 rounded-xl bg-surface-2/60 hover:bg-accent/10 border border-border/60 hover:border-accent/40 transition-all cursor-pointer group flex items-center justify-between"
            >
              <div className="space-y-1">
                <span className="text-xs font-extrabold text-text group-hover:text-accent transition-colors block">
                  {item.title}
                </span>
                <p className="text-xs text-text-muted font-mono">{item.query}</p>
                <p className="text-[10px] text-text-faint">{item.description}</p>
              </div>
              <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-accent group-hover:translate-x-0.5 transition-all flex-shrink-0" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
