import type { QueryLog } from '../types/query';
import type { BenchmarkQuestion, DailyQueryVolume, BenchmarkRunHistory } from '../types/benchmark';
import type { UserActivity } from '../types/user';

// 1. Initial Mock Query Logs (25 entries)
export const initialQueryLogs: QueryLog[] = ([
  {
    id: 'q-1',
    user: 'Farhan Hanif',
    question: 'Show the total sales for each product category.',
    generatedSql: 'SELECT category, SUM(line_total) AS total_sales FROM order_items JOIN products ON order_items.product_id = products.product_id GROUP BY category ORDER BY total_sales DESC;',
    executionTimeMs: 142,
    status: 'Success',
    timestamp: '2026-06-26T20:10:00+07:00',
    aiExplanation: 'I joined the `order_items` and `products` tables on `product_id`, grouped by the `category`, summed up the `line_total` for each, and ordered them from highest sales to lowest.',
    resultPreview: {
      columns: ['category', 'total_sales'],
      rows: [
        { category: 'Electronics', total_sales: 'Rp152,400,000' },
        { category: 'Apparel', total_sales: 'Rp98,150,000' },
        { category: 'Home & Living', total_sales: 'Rp76,900,000' },
        { category: 'Books', total_sales: 'Rp42,300,000' }
      ]
    }
  },
  {
    id: 'q-2',
    user: 'Siti Aminah',
    question: 'Who are the top 3 customers by total order amount?',
    generatedSql: 'SELECT name, SUM(order_total) AS total_spent FROM customers JOIN orders ON customers.customer_id = orders.customer_id GROUP BY name ORDER BY total_spent DESC LIMIT 3;',
    executionTimeMs: 185,
    status: 'Success',
    timestamp: '2026-06-26T20:05:12+07:00',
    aiExplanation: 'Joined the `customers` and `orders` tables on `customer_id`, grouped by `name`, calculated the sum of `order_total` as `total_spent`, and sorted descending with a limit of 3 rows.',
    resultPreview: {
      columns: ['name', 'total_spent'],
      rows: [
        { name: 'Budi Santoso', total_spent: 'Rp18,450,000' },
        { name: 'Dewi Lestari', total_spent: 'Rp15,200,000' },
        { name: 'Aditya Pratama', total_spent: 'Rp12,800,000' }
      ]
    }
  },
  {
    id: 'q-3',
    user: 'Rian Hidayat',
    question: 'Delete all rows from orders where status is cancelled.',
    generatedSql: 'DELETE FROM orders WHERE status = \'cancelled\';',
    executionTimeMs: 15,
    status: 'Failed',
    timestamp: '2026-06-26T20:01:45+07:00',
    errorDetail: 'Access Denied: The Database Agent operates in Read-Only mode. Non-SELECT queries are strictly prohibited.',
    aiExplanation: 'I detected a database mutation query (DELETE). To ensure database safety, I blocked execution and returned an authorization error.'
  },
  {
    id: 'q-4',
    user: 'Lina Wijaya',
    question: 'What is our overall database profit margin?',
    generatedSql: 'SELECT SUM(unit_price - cost) / SUM(unit_price) * 100 AS profit_margin FROM products;',
    executionTimeMs: 78,
    status: 'Success',
    timestamp: '2026-06-26T19:55:00+07:00',
    aiExplanation: 'Calculated the sum of differences between `unit_price` and `cost` across all products, and divided it by the sum of `unit_price` to obtain the average profit margin percentage.',
    resultPreview: {
      columns: ['profit_margin'],
      rows: [{ profit_margin: '38.45%' }]
    }
  },
  {
    id: 'q-5',
    user: 'Andi Wijaya',
    question: 'List completed orders from last month.',
    generatedSql: 'SELECT order_id, order_date, status, order_total FROM orders WHERE status = \'completed\' AND order_date >= date(\'now\', \'-1 month\');',
    executionTimeMs: 110,
    status: 'Success',
    timestamp: '2026-06-26T19:48:30+07:00',
    aiExplanation: 'Selected orders with a status of \'completed\' and filtered the `order_date` to be within the last month relative to today.',
    resultPreview: {
      columns: ['order_id', 'order_date', 'status', 'order_total'],
      rows: [
        { order_id: 10452, order_date: '2026-05-28', status: 'completed', order_total: 'Rp1,250,000' },
        { order_id: 10455, order_date: '2026-06-02', status: 'completed', order_total: 'Rp890,000' },
        { order_id: 10461, order_date: '2026-06-15', status: 'completed', order_total: 'Rp2,100,000' }
      ]
    }
  },
  {
    id: 'q-6',
    user: 'Siti Aminah',
    question: 'Count customers in Jakarta.',
    generatedSql: 'SELECT COUNT(*) AS customer_count FROM customers WHERE city = \'Jakarta\';',
    executionTimeMs: 65,
    status: 'Success',
    timestamp: '2026-06-26T19:30:10+07:00',
    aiExplanation: 'Counts all rows in the `customers` table where the `city` column equals \'Jakarta\'.',
    resultPreview: {
      columns: ['customer_count'],
      rows: [{ customer_count: 342 }]
    }
  },
  {
    id: 'q-7',
    user: 'Farhan Hanif',
    question: 'Average unit price of items sold in category Electronics.',
    generatedSql: 'SELECT AVG(order_items.unit_price) AS avg_sold_price FROM order_items JOIN products ON order_items.product_id = products.product_id WHERE products.category = \'Electronics\';',
    executionTimeMs: 205,
    status: 'Success',
    timestamp: '2026-06-26T19:22:18+07:00',
    resultPreview: {
      columns: ['avg_sold_price'],
      rows: [{ avg_sold_price: 'Rp1,560,000' }]
    }
  },
  {
    id: 'q-8',
    user: 'Rian Hidayat',
    question: 'Select * from payments where method equals GoPay but with status pending.',
    generatedSql: 'SELECT * FROM payments WHERE method = \'GoPay\' AND status = \'pending\';',
    executionTimeMs: 90,
    status: 'Success',
    timestamp: '2026-06-26T18:50:00+07:00',
    resultPreview: {
      columns: ['payment_id', 'order_id', 'amount', 'method', 'paid_date', 'status'],
      rows: [
        { payment_id: 8021, order_id: 10470, amount: 'Rp350,000', method: 'GoPay', paid_date: '2026-06-26', status: 'pending' },
        { payment_id: 8029, order_id: 10475, amount: 'Rp120,000', method: 'GoPay', paid_date: '2026-06-26', status: 'pending' }
      ]
    }
  },
  {
    id: 'q-9',
    user: 'Gita Lestari',
    question: 'Drop table customers;',
    generatedSql: 'DROP TABLE customers;',
    executionTimeMs: 8,
    status: 'Failed',
    timestamp: '2026-06-26T18:42:11+07:00',
    errorDetail: 'Access Denied: The Database Agent operates in Read-Only mode. DROP queries are strictly prohibited.',
    aiExplanation: 'Detected database schema drop instruction. This query was blocked by the safety layer.'
  },
  {
    id: 'q-10',
    user: 'Lina Wijaya',
    question: 'Find the product with ID 105.',
    generatedSql: 'SELECT * FROM products WHERE product_id = 105;',
    executionTimeMs: 50,
    status: 'Success',
    timestamp: '2026-06-26T18:15:30+07:00',
    resultPreview: {
      columns: ['product_id', 'product_name', 'category', 'unit_price', 'cost'],
      rows: [
        { product_id: 105, product_name: 'Wireless Mouse Pro', category: 'Electronics', unit_price: 'Rp350,000', cost: 'Rp220,000' }
      ]
    }
  },
  {
    id: 'q-11',
    user: 'Eko Prasetyo',
    question: 'Total items sold by category.',
    generatedSql: 'SELECT category, SUM(quantity) AS total_qty FROM order_items JOIN products ON order_items.product_id = products.product_id GROUP BY category;',
    executionTimeMs: 154,
    status: 'Success',
    timestamp: '2026-06-26T17:40:00+07:00',
    resultPreview: {
      columns: ['category', 'total_qty'],
      rows: [
        { category: 'Electronics', total_qty: 4890 },
        { category: 'Apparel', total_qty: 12400 },
        { category: 'Home & Living', total_qty: 5600 },
        { category: 'Books', total_qty: 3200 }
      ]
    }
  },
  {
    id: 'q-12',
    user: 'Andi Wijaya',
    question: 'List customer tiers and the count of users in each tier.',
    generatedSql: 'SELECT tier, COUNT(*) AS count FROM customers GROUP BY tier;',
    executionTimeMs: 72,
    status: 'Success',
    timestamp: '2026-06-26T17:12:05+07:00',
    resultPreview: {
      columns: ['tier', 'count'],
      rows: [
        { tier: 'Bronze', count: 480 },
        { tier: 'Silver', count: 320 },
        { tier: 'Gold', count: 180 },
        { tier: 'Platinum', count: 20 }
      ]
    }
  },
  {
    id: 'q-13',
    user: 'Eko Prasetyo',
    question: 'Select payments where method is ShopeePay.',
    generatedSql: 'SELECT payment_id, amount, paid_date FROM payments WHERE method = \'ShopeePay\' LIMIT 3;',
    executionTimeMs: 82,
    status: 'Success',
    timestamp: '2026-06-26T16:50:20+07:00',
    resultPreview: {
      columns: ['payment_id', 'amount', 'paid_date'],
      rows: [
        { payment_id: 8001, amount: 'Rp150,000', paid_date: '2026-06-25' },
        { payment_id: 8004, amount: 'Rp280,000', paid_date: '2026-06-25' },
        { payment_id: 8011, amount: 'Rp85,000', paid_date: '2026-06-26' }
      ]
    }
  },
  {
    id: 'q-14',
    user: 'Farhan Hanif',
    question: 'List products where unit price is greater than 10 million IDR.',
    generatedSql: 'SELECT product_name, unit_price FROM products WHERE unit_price > 10000000;',
    executionTimeMs: 60,
    status: 'Success',
    timestamp: '2026-06-26T15:44:00+07:00',
    resultPreview: {
      columns: ['product_name', 'unit_price'],
      rows: [
        { product_name: 'MacBook Pro 16" M3', unit_price: 'Rp35,999,000' },
        { product_name: 'iPhone 15 Pro Max 512GB', unit_price: 'Rp24,999,000' },
        { product_name: 'Sony A7 IV Camera', unit_price: 'Rp31,500,000' }
      ]
    }
  },
  {
    id: 'q-15',
    user: 'Siti Aminah',
    question: 'What is the sum of order_total in 2024?',
    generatedSql: 'SELECT SUM(order_total) AS total_sales_2024 FROM orders WHERE strftime(\'%Y\', order_date) = \'2024\';',
    executionTimeMs: 110,
    status: 'Success',
    timestamp: '2026-06-26T15:30:12+07:00',
    resultPreview: {
      columns: ['total_sales_2024'],
      rows: [{ total_sales_2024: 'Rp1,425,800,000' }]
    }
  },
  {
    id: 'q-16',
    user: 'Rian Hidayat',
    question: 'Show the total cost of all orders that are completed.',
    generatedSql: 'SELECT SUM(cost * quantity) AS total_cost FROM order_items JOIN products ON order_items.product_id = products.product_id JOIN orders ON order_items.order_id = orders.order_id WHERE orders.status = \'completed\';',
    executionTimeMs: 232,
    status: 'Success',
    timestamp: '2026-06-26T14:15:00+07:00',
    resultPreview: {
      columns: ['total_cost'],
      rows: [{ total_cost: 'Rp945,620,000' }]
    }
  },
  {
    id: 'q-17',
    user: 'Gita Lestari',
    question: 'Find orders with total greater than 5 million.',
    generatedSql: 'SELECT order_id, order_total FROM orders WHERE order_total > 5000000 ORDER BY order_total DESC LIMIT 3;',
    executionTimeMs: 95,
    status: 'Success',
    timestamp: '2026-06-26T13:20:45+07:00',
    resultPreview: {
      columns: ['order_id', 'order_total'],
      rows: [
        { order_id: 10240, order_total: 'Rp8,400,000' },
        { order_id: 10311, order_total: 'Rp6,150,000' },
        { order_id: 10129, order_total: 'Rp5,900,000' }
      ]
    }
  },
  {
    id: 'q-18',
    user: 'Eko Prasetyo',
    question: 'Update product cost to 0 where ID is 12.',
    generatedSql: 'UPDATE products SET cost = 0 WHERE product_id = 12;',
    executionTimeMs: 12,
    status: 'Failed',
    timestamp: '2026-06-26T12:05:00+07:00',
    errorDetail: 'Access Denied: The Database Agent operates in Read-Only mode. UPDATE queries are strictly prohibited.',
    aiExplanation: 'Detected database update instruction. This query was blocked by the safety layer.'
  },
  {
    id: 'q-19',
    user: 'Dewi Sartika',
    question: 'List categories with average price of products.',
    generatedSql: 'SELECT category, AVG(unit_price) AS avg_price FROM products GROUP BY category;',
    executionTimeMs: 62,
    status: 'Success',
    timestamp: '2026-06-26T11:42:15+07:00',
    resultPreview: {
      columns: ['category', 'avg_price'],
      rows: [
        { category: 'Electronics', avg_price: 'Rp4,820,000' },
        { category: 'Apparel', avg_price: 'Rp280,000' },
        { category: 'Home & Living', avg_price: 'Rp620,000' },
        { category: 'Books', avg_price: 'Rp110,000' }
      ]
    }
  },
  {
    id: 'q-20',
    user: 'Dewi Sartika',
    question: 'Find customers from Bandung tier Gold.',
    generatedSql: 'SELECT customer_id, name, created_at FROM customers WHERE city = \'Bandung\' AND tier = \'Gold\';',
    executionTimeMs: 84,
    status: 'Success',
    timestamp: '2026-06-26T10:10:00+07:00',
    resultPreview: {
      columns: ['customer_id', 'name', 'created_at'],
      rows: [
        { customer_id: 203, name: 'Hendra Setiawan', created_at: '2024-01-15' },
        { customer_id: 409, name: 'Sinta Nuriyah', created_at: '2024-04-10' }
      ]
    }
  },
  {
    id: 'q-21',
    user: 'Farhan Hanif',
    question: 'List completed orders with cash payment method.',
    generatedSql: 'SELECT orders.order_id, order_total FROM orders JOIN payments ON orders.order_id = payments.order_id WHERE orders.status = \'completed\' AND payments.method = \'cash\';',
    executionTimeMs: 148,
    status: 'Success',
    timestamp: '2026-06-26T09:40:12+07:00',
    resultPreview: {
      columns: ['order_id', 'order_total'],
      rows: [
        { order_id: 10401, order_total: 'Rp120,000' },
        { order_id: 10410, order_total: 'Rp350,000' }
      ]
    }
  },
  {
    id: 'q-22',
    user: 'Rian Hidayat',
    question: 'Select products that cost less than 50 thousand rupiah.',
    generatedSql: 'SELECT product_id, product_name, unit_price FROM products WHERE unit_price < 50000 LIMIT 3;',
    executionTimeMs: 44,
    status: 'Success',
    timestamp: '2026-06-26T08:15:00+07:00',
    resultPreview: {
      columns: ['product_id', 'product_name', 'unit_price'],
      rows: [
        { product_id: 45, product_name: 'Sticky Notes Blue', unit_price: 'Rp12,000' },
        { product_id: 89, product_name: 'Gel Pen Black', unit_price: 'Rp8,500' },
        { product_id: 111, product_name: 'A4 Notebook 80 Sheets', unit_price: 'Rp22,000' }
      ]
    }
  },
  {
    id: 'q-23',
    user: 'Siti Aminah',
    question: 'List payment methods and sum of amount.',
    generatedSql: 'SELECT method, SUM(amount) AS total_amount FROM payments GROUP BY method;',
    executionTimeMs: 120,
    status: 'Success',
    timestamp: '2026-06-26T07:30:22+07:00',
    resultPreview: {
      columns: ['method', 'total_amount'],
      rows: [
        { method: 'GoPay', total_amount: 'Rp542,800,000' },
        { method: 'OVO', total_amount: 'Rp241,500,000' },
        { method: 'ShopeePay', total_amount: 'Rp182,300,000' },
        { method: 'Credit Card', total_amount: 'Rp845,900,000' },
        { method: 'Bank Transfer', total_amount: 'Rp1,240,500,000' }
      ]
    }
  },
  {
    id: 'q-24',
    user: 'Andi Wijaya',
    question: 'Select customers whose name starts with B.',
    generatedSql: 'SELECT customer_id, name, city FROM customers WHERE name LIKE \'B%\' LIMIT 3;',
    executionTimeMs: 58,
    status: 'Success',
    timestamp: '2026-06-26T06:12:11+07:00',
    resultPreview: {
      columns: ['customer_id', 'name', 'city'],
      rows: [
        { customer_id: 12, name: 'Budi Santoso', city: 'Jakarta' },
        { customer_id: 54, name: ' Bambang Pamungkas', city: 'Surabaya' },
        { customer_id: 98, name: 'Bella Chandra', city: 'Medan' }
      ]
    }
  },
  {
    id: 'q-25',
    user: 'Gita Lestari',
    question: 'Insert into products values (999, \'Test Product\', \'Other\', 10000, 5000);',
    generatedSql: 'INSERT INTO products VALUES (999, \'Test Product\', \'Other\', 10000, 5000);',
    executionTimeMs: 14,
    status: 'Failed',
    timestamp: '2026-06-26T05:55:00+07:00',
    errorDetail: 'Access Denied: The Database Agent operates in Read-Only mode. INSERT queries are strictly prohibited.',
    aiExplanation: 'Detected database insert statement. Blocked by the read-only security filter.'
  }
] as any[]).map(log => {
  const guardrailStatus: 'Allowed' | 'Blocked' = log.status === 'Success' ? 'Allowed' : 'Blocked';
  let guardrailReason = undefined;
  
  if (guardrailStatus === 'Blocked') {
    const qLower = log.question.toLowerCase();
    if (qLower.includes('delete')) {
      guardrailReason = 'DELETE statement detected';
    } else if (qLower.includes('drop')) {
      guardrailReason = 'DROP statement detected';
    } else if (qLower.includes('update')) {
      guardrailReason = 'UPDATE statement detected';
    } else if (qLower.includes('insert')) {
      guardrailReason = 'INSERT statement detected';
    } else {
      guardrailReason = 'DDL statement detected';
    }
  }
  
  let clarificationHistory = undefined;
  if (log.id === 'q-11') {
    clarificationHistory = {
      originalPrompt: 'how many items did we sell?',
      clarificationQuestion: 'Would you like the total number of items sold grouped by product category, or individual products?',
      userResponse: 'by category',
      finalPrompt: 'Total items sold by category.'
    };
  } else if (log.id === 'q-21') {
    clarificationHistory = {
      originalPrompt: 'list orders that were paid with cash',
      clarificationQuestion: 'Should this list include all orders or only those that are currently completed?',
      userResponse: 'only completed ones',
      finalPrompt: 'List completed orders with cash payment method.'
    };
  }
  
  return {
    ...log,
    guardrailStatus,
    guardrailReason,
    clarificationHistory
  } as QueryLog;
});

// 2. Benchmark Questions (The 52 standard evaluation questions)
export const initialBenchmarkQuestions: BenchmarkQuestion[] = [
  {
    id: 'bq-1',
    question: 'Show the total sales for each product category.',
    expectedSql: 'SELECT category, SUM(line_total) AS total_sales FROM order_items JOIN products ON order_items.product_id = products.product_id GROUP BY category ORDER BY total_sales DESC;',
    generatedSql: 'SELECT category, SUM(line_total) AS total_sales FROM order_items JOIN products ON order_items.product_id = products.product_id GROUP BY category ORDER BY total_sales DESC;',
    result: 'Correct',
    responseTimeMs: 142,
    expectedAnswer: 'Computes total revenue grouped by categories (Electronics, Apparel, etc.) in descending order.',
    tablesUsed: ['order_items', 'products'],
    timestamp: '2026-06-26T15:00:00+07:00',
    resultPreview: {
      columns: ['category', 'total_sales'],
      rows: [
        { category: 'Electronics', total_sales: 'Rp152,400,000' },
        { category: 'Apparel', total_sales: 'Rp98,150,000' },
        { category: 'Home & Living', total_sales: 'Rp76,900,000' },
        { category: 'Books', total_sales: 'Rp42,300,000' }
      ]
    }
  },
  {
    id: 'bq-2',
    question: 'Who are the top 5 customers by total order amount?',
    expectedSql: 'SELECT name, SUM(order_total) AS total_spent FROM customers JOIN orders ON customers.customer_id = orders.customer_id GROUP BY name ORDER BY total_spent DESC LIMIT 5;',
    generatedSql: 'SELECT name, SUM(order_total) AS total_spent FROM customers JOIN orders ON customers.customer_id = orders.customer_id GROUP BY name ORDER BY total_spent DESC LIMIT 5;',
    result: 'Correct',
    responseTimeMs: 185,
    expectedAnswer: 'Identifies the highest spending buyers with their total accumulated transaction totals.',
    tablesUsed: ['customers', 'orders'],
    timestamp: '2026-06-26T15:01:22+07:00',
    resultPreview: {
      columns: ['name', 'total_spent'],
      rows: [
        { name: 'Budi Santoso', total_spent: 'Rp18,450,000' },
        { name: 'Dewi Lestari', total_spent: 'Rp15,200,000' },
        { name: 'Aditya Pratama', total_spent: 'Rp12,800,000' },
        { name: 'Farhan Hanif', total_spent: 'Rp10,500,000' },
        { name: 'Lina Wijaya', total_spent: 'Rp9,800,000' }
      ]
    }
  },
  {
    id: 'bq-3',
    question: 'List all orders that are completed and paid with credit card.',
    expectedSql: 'SELECT orders.order_id, order_date, order_total FROM orders JOIN payments ON orders.order_id = payments.order_id WHERE orders.status = \'completed\' AND payments.method = \'credit card\';',
    generatedSql: 'SELECT orders.order_id, order_date, order_total FROM orders JOIN payments ON orders.order_id = payments.order_id WHERE orders.status = \'completed\' AND payments.method = \'credit card\';',
    result: 'Correct',
    responseTimeMs: 154,
    expectedAnswer: 'Filters transactions by status = \'completed\' and payment method = \'credit card\'.',
    tablesUsed: ['orders', 'payments'],
    timestamp: '2026-06-26T15:02:40+07:00',
    resultPreview: {
      columns: ['order_id', 'order_date', 'order_total'],
      rows: [
        { order_id: 10001, order_date: '2026-06-15', order_total: 'Rp25,999,000' },
        { order_id: 10003, order_date: '2026-06-20', order_total: 'Rp1,850,000' }
      ]
    }
  },
  {
    id: 'bq-4',
    question: 'How many orders were placed by customers in Jakarta?',
    expectedSql: 'SELECT COUNT(*) AS order_count FROM orders JOIN customers ON orders.customer_id = customers.customer_id WHERE city = \'Jakarta\';',
    generatedSql: 'SELECT COUNT(order_id) AS order_count FROM orders JOIN customers ON orders.customer_id = customers.customer_id WHERE customers.city = \'Jakarta\';',
    result: 'Correct',
    responseTimeMs: 95,
    expectedAnswer: 'Counts orders originating from customers residing in the Jakarta area.',
    tablesUsed: ['orders', 'customers'],
    timestamp: '2026-06-26T15:03:10+07:00',
    resultPreview: {
      columns: ['order_count'],
      rows: [{ order_count: 5 }]
    }
  },
  {
    id: 'bq-5',
    question: 'What is the average profit margin for each product category?',
    expectedSql: 'SELECT category, AVG((unit_price - cost) / unit_price) * 100 AS avg_margin FROM products GROUP BY category;',
    generatedSql: 'SELECT category, AVG(unit_price - cost) / AVG(unit_price) * 100 AS avg_margin FROM products GROUP BY category;',
    result: 'Incorrect',
    responseTimeMs: 120,
    expectedAnswer: 'Groups products and calculates margins as a percentage: (price - cost) / price.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:04:15+07:00',
    errorDetail: 'Execution Result Mismatch: Gold answer returned 35.8%, generated query returned 38.2%.'
  },
  {
    id: 'bq-6',
    question: 'Find products that have never been ordered.',
    expectedSql: 'SELECT product_name FROM products LEFT JOIN order_items ON products.product_id = order_items.product_id WHERE order_items.product_id IS NULL;',
    generatedSql: 'SELECT product_name FROM products LEFT JOIN order_items ON products.product_id = order_items.product_id WHERE order_items.product_id IS NULL;',
    result: 'Correct',
    responseTimeMs: 110,
    expectedAnswer: 'Identifies catalog products without any matching entries in the order items table.',
    tablesUsed: ['products', 'order_items'],
    timestamp: '2026-06-26T15:05:00+07:00',
    resultPreview: {
      columns: ['product_name'],
      rows: [
        { product_name: 'Coffee Maker Espresso' }
      ]
    }
  },
  {
    id: 'bq-7',
    question: 'Which payment method is used most frequently?',
    expectedSql: 'SELECT method, COUNT(*) AS usage_count FROM payments GROUP BY method ORDER BY usage_count DESC LIMIT 1;',
    generatedSql: 'SELECT method FROM payments GROUP BY method ORDER BY COUNT(*) DESC LIMIT 1;',
    result: 'Correct',
    responseTimeMs: 76,
    expectedAnswer: 'Calculates the payment method with the highest transaction count.',
    tablesUsed: ['payments'],
    timestamp: '2026-06-26T15:06:11+07:00',
    resultPreview: {
      columns: ['method', 'usage_count'],
      rows: [{ method: 'GoPay', usage_count: 6 }]
    }
  },
  {
    id: 'bq-8',
    question: 'Show monthly sales for the year 2023.',
    expectedSql: 'SELECT strftime(\'%m\', order_date) AS month, SUM(order_total) AS total_sales FROM orders WHERE strftime(\'%Y\', order_date) = \'2023\' GROUP BY month ORDER BY month;',
    generatedSql: 'SELECT strftime(\'%m\', order_date) AS month, SUM(order_total) FROM orders WHERE order_date LIKE \'2023-%\' GROUP BY month ORDER BY month;',
    result: 'Correct',
    responseTimeMs: 160,
    expectedAnswer: 'Groups transactions by month and sums the totals for orders placed in 2023.',
    tablesUsed: ['orders'],
    timestamp: '2026-06-26T15:07:30+07:00',
    resultPreview: {
      columns: ['month', 'total_sales'],
      rows: [
        { month: '01', total_sales: 'Rp18,900,000' },
        { month: '02', total_sales: 'Rp12,400,000' }
      ]
    }
  },
  {
    id: 'bq-9',
    question: 'What is the average order value for Gold tier customers?',
    expectedSql: 'SELECT AVG(order_total) AS avg_order FROM orders JOIN customers ON orders.customer_id = customers.customer_id WHERE tier = \'Gold\';',
    generatedSql: 'SELECT AVG(order_total) AS avg_order FROM orders JOIN customers ON orders.customer_id = customers.customer_id WHERE customers.tier = \'Gold\';',
    result: 'Correct',
    responseTimeMs: 94,
    expectedAnswer: 'Joins orders and customers to find the average order_total for customers in the Gold tier.',
    tablesUsed: ['orders', 'customers'],
    timestamp: '2026-06-26T15:08:45+07:00',
    resultPreview: {
      columns: ['avg_order'],
      rows: [{ avg_order: 'Rp18,249,000' }]
    }
  },
  {
    id: 'bq-10',
    question: 'List the top 3 most popular products by quantity sold.',
    expectedSql: 'SELECT product_name, SUM(quantity) AS total_qty FROM order_items JOIN products ON order_items.product_id = products.product_id GROUP BY product_name ORDER BY total_qty DESC LIMIT 3;',
    generatedSql: 'SELECT product_name, SUM(quantity) AS total_qty FROM order_items JOIN products ON order_items.product_id = products.product_id GROUP BY product_name ORDER BY total_qty LIMIT 3;',
    result: 'Incorrect',
    responseTimeMs: 135,
    expectedAnswer: 'Sums quantities sold grouped by product, sorted in descending order with a limit of 3.',
    tablesUsed: ['order_items', 'products'],
    timestamp: '2026-06-26T15:09:12+07:00',
    errorDetail: 'Execution Result Mismatch: Missing DESC sorting order in generated SQL. Results sorted in ascending order.'
  },
  {
    id: 'bq-11',
    question: 'Which cities have customers who spent more than 50,000,000 IDR in total?',
    expectedSql: 'SELECT city, SUM(order_total) AS total_spent FROM customers JOIN orders ON customers.customer_id = orders.customer_id GROUP BY city HAVING total_spent > 50000000;',
    generatedSql: 'SELECT city, SUM(order_total) AS total_spent FROM customers JOIN orders ON customers.customer_id = orders.customer_id GROUP BY city HAVING SUM(order_total) > 50000000;',
    result: 'Correct',
    responseTimeMs: 148,
    expectedAnswer: 'Groups customers by city, filters groups where total order totals exceed 50 million.',
    tablesUsed: ['customers', 'orders'],
    timestamp: '2026-06-26T15:10:05+07:00',
    resultPreview: {
      columns: ['city', 'total_spent'],
      rows: [
        { city: 'Jakarta', total_spent: 'Rp54,249,000' }
      ]
    }
  },
  {
    id: 'bq-12',
    question: 'What is the total quantity of \'Electronics\' products sold?',
    expectedSql: 'SELECT SUM(quantity) AS total_sold FROM order_items JOIN products ON order_items.product_id = products.product_id WHERE category = \'Electronics\';',
    generatedSql: 'SELECT SUM(quantity) FROM order_items JOIN products ON order_items.product_id = products.product_id WHERE category = \'Electronics\';',
    result: 'Correct',
    responseTimeMs: 104,
    expectedAnswer: 'Aggregates quantities sold for items classified under the Electronics category.',
    tablesUsed: ['order_items', 'products'],
    timestamp: '2026-06-26T15:11:00+07:00',
    resultPreview: {
      columns: ['total_sold'],
      rows: [{ total_sold: 12 }]
    }
  },
  {
    id: 'bq-13',
    question: 'List customers who registered in 2023 and have placed at least 3 orders.',
    expectedSql: 'SELECT name, COUNT(order_id) AS num_orders FROM customers JOIN orders ON customers.customer_id = orders.customer_id WHERE strftime(\'%Y\', created_at) = \'2023\' GROUP BY name HAVING num_orders >= 3;',
    generatedSql: 'SELECT name, COUNT(order_id) AS num_orders FROM customers JOIN orders ON customers.customer_id = orders.customer_id WHERE created_at LIKE \'2023-%\' GROUP BY name HAVING COUNT(order_id) >= 3;',
    result: 'Correct',
    responseTimeMs: 198,
    expectedAnswer: 'Identifies buyers registered in 2023 with a minimum order count of 3.',
    tablesUsed: ['customers', 'orders'],
    timestamp: '2026-06-26T15:12:00+07:00',
    resultPreview: {
      columns: ['name', 'num_orders'],
      rows: [
        { name: 'Farhan Hanif', num_orders: 4 }
      ]
    }
  },
  {
    id: 'bq-14',
    question: 'What is the total refund amount due to refunded payments?',
    expectedSql: 'SELECT SUM(amount) AS total_refunded FROM payments WHERE status = \'refunded\';',
    generatedSql: 'SELECT SUM(amount) FROM payments WHERE status = \'refunded\' AND method = \'cash\';',
    result: 'Incorrect',
    responseTimeMs: 82,
    expectedAnswer: 'Sums up the total payment amount where transaction status is refunded.',
    tablesUsed: ['payments'],
    timestamp: '2026-06-26T15:13:00+07:00',
    errorDetail: 'Execution Result Mismatch: Generated SQL incorrectly filtered payments by method = \'cash\'.'
  },
  {
    id: 'bq-15',
    question: 'Find the top 5 order items with the highest line total.',
    expectedSql: 'SELECT product_name, line_total FROM order_items JOIN products ON order_items.product_id = products.product_id ORDER BY line_total DESC LIMIT 5;',
    generatedSql: 'SELECT product_name, line_total FROM order_items JOIN products ON order_items.product_id = products.product_id ORDER BY line_total DESC LIMIT 5;',
    result: 'Correct',
    responseTimeMs: 130,
    expectedAnswer: 'Retrieves product names and order line totals, sorted descending, returning the top 5 rows.',
    tablesUsed: ['order_items', 'products'],
    timestamp: '2026-06-26T15:14:00+07:00',
    resultPreview: {
      columns: ['product_name', 'line_total'],
      rows: [
        { product_name: 'MacBook Pro 14" M3', line_total: 'Rp25,999,000' },
        { product_name: 'iPhone 15 Pro Max', line_total: 'Rp19,999,000' }
      ]
    }
  },
  {
    id: 'bq-16',
    question: 'Select all columns from products.',
    expectedSql: 'SELECT * FROM products;',
    generatedSql: 'SELECT * FROM products;',
    result: 'Correct',
    responseTimeMs: 45,
    expectedAnswer: 'Retrieves all catalog rows with all details.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:15:00+07:00',
    resultPreview: {
      columns: ['product_id', 'product_name', 'category', 'unit_price', 'cost'],
      rows: [{ product_id: 101, product_name: 'MacBook Pro 14" M3', category: 'Electronics', unit_price: 25999000, cost: 18500000 }]
    }
  },
  {
    id: 'bq-17',
    question: 'Show all payment records.',
    expectedSql: 'SELECT * FROM payments;',
    generatedSql: 'SELECT * FROM payments;',
    result: 'Correct',
    responseTimeMs: 50,
    expectedAnswer: 'Queries the entire payments log history.',
    tablesUsed: ['payments'],
    timestamp: '2026-06-26T15:16:00+07:00'
  },
  {
    id: 'bq-18',
    question: 'List all orders.',
    expectedSql: 'SELECT * FROM orders;',
    generatedSql: 'SELECT * FROM orders;',
    result: 'Correct',
    responseTimeMs: 55,
    expectedAnswer: 'Queries the complete sales transactions list.',
    tablesUsed: ['orders'],
    timestamp: '2026-06-26T15:17:00+07:00'
  },
  {
    id: 'bq-19',
    question: 'List all customer details.',
    expectedSql: 'SELECT * FROM customers;',
    generatedSql: 'SELECT * FROM customers;',
    result: 'Correct',
    responseTimeMs: 60,
    expectedAnswer: 'Queries the complete client database records.',
    tablesUsed: ['customers'],
    timestamp: '2026-06-26T15:18:00+07:00'
  },
  {
    id: 'bq-20',
    question: 'Find products in the category \'Electronics\' with unit price above 15 million.',
    expectedSql: 'SELECT * FROM products WHERE category = \'Electronics\' AND unit_price > 15000000;',
    generatedSql: 'SELECT * FROM products WHERE category = \'Electronics\' AND unit_price > 15000000;',
    result: 'Correct',
    responseTimeMs: 82,
    expectedAnswer: 'Applies filter criteria to catalog table.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:19:00+07:00'
  },
  {
    id: 'bq-21',
    question: 'List orders with total above 5 million.',
    expectedSql: 'SELECT * FROM orders WHERE order_total > 5000000;',
    generatedSql: 'SELECT * FROM orders WHERE order_total > 5000000;',
    result: 'Correct',
    responseTimeMs: 70,
    expectedAnswer: 'Applies value threshold filters to order records.',
    tablesUsed: ['orders'],
    timestamp: '2026-06-26T15:20:00+07:00'
  },
  {
    id: 'bq-22',
    question: 'Find customers located in Bandung.',
    expectedSql: 'SELECT * FROM customers WHERE city = \'Bandung\';',
    generatedSql: 'SELECT * FROM customers WHERE city = \'Bandung\';',
    result: 'Correct',
    responseTimeMs: 65,
    expectedAnswer: 'Filters accounts by Bandung city location.',
    tablesUsed: ['customers'],
    timestamp: '2026-06-26T15:21:00+07:00'
  },
  {
    id: 'bq-23',
    question: 'Show completed orders from customer 1.',
    expectedSql: 'SELECT * FROM orders WHERE customer_id = 1 AND status = \'completed\';',
    generatedSql: 'SELECT * FROM orders WHERE customer_id = 1 AND status = \'completed\';',
    result: 'Correct',
    responseTimeMs: 73,
    expectedAnswer: 'Filters transactions by customer ID and completed status.',
    tablesUsed: ['orders'],
    timestamp: '2026-06-26T15:22:00+07:00'
  },
  {
    id: 'bq-24',
    question: 'Show payments made using GoPay.',
    expectedSql: 'SELECT * FROM payments WHERE method = \'GoPay\';',
    generatedSql: 'SELECT * FROM payments WHERE method = \'GoPay\';',
    result: 'Correct',
    responseTimeMs: 58,
    expectedAnswer: 'Filters payment records by method GoPay.',
    tablesUsed: ['payments'],
    timestamp: '2026-06-26T15:23:00+07:00'
  },
  {
    id: 'bq-25',
    question: 'Show products ordered by unit price descending.',
    expectedSql: 'SELECT * FROM products ORDER BY unit_price DESC;',
    generatedSql: 'SELECT * FROM products ORDER BY unit_price DESC;',
    result: 'Correct',
    responseTimeMs: 69,
    expectedAnswer: 'Sorts products by pricing descending.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:24:00+07:00'
  },
  {
    id: 'bq-26',
    question: 'List customers ordered by name alphabetically.',
    expectedSql: 'SELECT * FROM customers ORDER BY name ASC;',
    generatedSql: 'SELECT * FROM customers ORDER BY name ASC;',
    result: 'Correct',
    responseTimeMs: 78,
    expectedAnswer: 'Sorts accounts alphabetically by name.',
    tablesUsed: ['customers'],
    timestamp: '2026-06-26T15:25:00+07:00'
  },
  {
    id: 'bq-27',
    question: 'Show orders sorted by date descending.',
    expectedSql: 'SELECT * FROM orders ORDER BY order_date DESC;',
    generatedSql: 'SELECT * FROM orders ORDER BY order_date DESC;',
    result: 'Correct',
    responseTimeMs: 85,
    expectedAnswer: 'Sorts transactions chronologically from newest to oldest.',
    tablesUsed: ['orders'],
    timestamp: '2026-06-26T15:26:00+07:00'
  },
  {
    id: 'bq-28',
    question: 'List products in category \'Books\' ordered by cost ascending.',
    expectedSql: 'SELECT * FROM products WHERE category = \'Books\' ORDER BY cost ASC;',
    generatedSql: 'SELECT * FROM products WHERE category = \'Books\' ORDER BY cost ASC;',
    result: 'Correct',
    responseTimeMs: 91,
    expectedAnswer: 'Filters products by category and sorts by cost ascending.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:27:00+07:00'
  },
  {
    id: 'bq-29',
    question: 'Show the total number of products in each category.',
    expectedSql: 'SELECT category, COUNT(*) AS product_count FROM products GROUP BY category;',
    generatedSql: 'SELECT category, COUNT(*) AS product_count FROM products GROUP BY category;',
    result: 'Correct',
    responseTimeMs: 102,
    expectedAnswer: 'Groups and counts products across categories.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:28:00+07:00'
  },
  {
    id: 'bq-30',
    question: 'What is the average price of products in Home & Living?',
    expectedSql: 'SELECT AVG(unit_price) AS avg_price FROM products WHERE category = \'Home & Living\';',
    generatedSql: 'SELECT AVG(unit_price) AS avg_price FROM products WHERE category = \'Home & Living\';',
    result: 'Correct',
    responseTimeMs: 110,
    expectedAnswer: 'Averages pricing for Home & Living catalog items.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:29:00+07:00'
  },
  {
    id: 'bq-31',
    question: 'What is the maximum cost of any product?',
    expectedSql: 'SELECT MAX(cost) AS max_cost FROM products;',
    generatedSql: 'SELECT MAX(cost) AS max_cost FROM products;',
    result: 'Correct',
    responseTimeMs: 88,
    expectedAnswer: 'Finds the highest production cost in catalog.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:30:00+07:00'
  },
  {
    id: 'bq-32',
    question: 'Show total sales by order status.',
    expectedSql: 'SELECT status, SUM(order_total) AS total_sales FROM orders GROUP BY status;',
    generatedSql: 'SELECT status, SUM(order_total) AS total_sales FROM orders GROUP BY status;',
    result: 'Correct',
    responseTimeMs: 120,
    expectedAnswer: 'Summarizes order totals grouped by status.',
    tablesUsed: ['orders'],
    timestamp: '2026-06-26T15:31:00+07:00'
  },
  {
    id: 'bq-33',
    question: 'Count payments grouped by status.',
    expectedSql: 'SELECT status, COUNT(*) AS payment_count FROM payments GROUP BY status;',
    generatedSql: 'SELECT status, COUNT(*) AS payment_count FROM payments GROUP BY status;',
    result: 'Correct',
    responseTimeMs: 95,
    expectedAnswer: 'Counts payment records grouped by status.',
    tablesUsed: ['payments'],
    timestamp: '2026-06-26T15:32:00+07:00'
  },
  {
    id: 'bq-34',
    question: 'Show the minimum order total for completed orders.',
    expectedSql: 'SELECT MIN(order_total) AS min_total FROM orders WHERE status = \'completed\';',
    generatedSql: 'SELECT MIN(order_total) AS min_total FROM orders WHERE status = \'completed\';',
    result: 'Correct',
    responseTimeMs: 84,
    expectedAnswer: 'Finds lowest completed order total.',
    tablesUsed: ['orders'],
    timestamp: '2026-06-26T15:33:00+07:00'
  },
  {
    id: 'bq-35',
    question: 'Show order ID and customer name for each order.',
    expectedSql: 'SELECT orders.order_id, customers.name FROM orders JOIN customers ON orders.customer_id = customers.customer_id;',
    generatedSql: 'SELECT orders.order_id, customers.name FROM orders JOIN customers ON orders.customer_id = customers.customer_id;',
    result: 'Correct',
    responseTimeMs: 135,
    expectedAnswer: 'Joins orders and customers to map buyer names to transactions.',
    tablesUsed: ['orders', 'customers'],
    timestamp: '2026-06-26T15:34:00+07:00'
  },
  {
    id: 'bq-36',
    question: 'List products sold along with their categories and quantities.',
    expectedSql: 'SELECT products.product_name, products.category, order_items.quantity FROM order_items JOIN products ON order_items.product_id = products.product_id;',
    generatedSql: 'SELECT products.product_name, products.category, order_items.quantity FROM order_items JOIN products ON order_items.product_id = products.product_id;',
    result: 'Correct',
    responseTimeMs: 145,
    expectedAnswer: 'Joins order items and products to fetch names, categories, and quantities.',
    tablesUsed: ['order_items', 'products'],
    timestamp: '2026-06-26T15:35:00+07:00'
  },
  {
    id: 'bq-37',
    question: 'Find payments and their associated order totals.',
    expectedSql: 'SELECT payments.payment_id, orders.order_total FROM payments JOIN orders ON payments.order_id = orders.order_id;',
    generatedSql: 'SELECT payments.payment_id, orders.order_total FROM payments JOIN orders ON payments.order_id = orders.order_id;',
    result: 'Correct',
    responseTimeMs: 110,
    expectedAnswer: 'Joins payments and orders to verify transaction totals.',
    tablesUsed: ['payments', 'orders'],
    timestamp: '2026-06-26T15:36:00+07:00'
  },
  {
    id: 'bq-38',
    question: 'List order date, customer name, and total amount for all transactions.',
    expectedSql: 'SELECT orders.order_date, customers.name, orders.order_total FROM orders JOIN customers ON orders.customer_id = customers.customer_id;',
    generatedSql: 'SELECT orders.order_date, customers.name, orders.order_total FROM orders JOIN customers ON orders.customer_id = customers.customer_id;',
    result: 'Correct',
    responseTimeMs: 155,
    expectedAnswer: 'Joins orders and customers to map transactions to customer names.',
    tablesUsed: ['orders', 'customers'],
    timestamp: '2026-06-26T15:37:00+07:00'
  },
  {
    id: 'bq-39',
    question: 'Show product name, quantity sold, and customer city for all orders.',
    expectedSql: 'SELECT products.product_name, order_items.quantity, customers.city FROM order_items JOIN products ON order_items.product_id = products.product_id JOIN orders ON order_items.order_id = orders.order_id JOIN customers ON orders.customer_id = customers.customer_id;',
    generatedSql: 'SELECT products.product_name, order_items.quantity, customers.city FROM order_items JOIN products ON order_items.product_id = products.product_id JOIN orders ON order_items.order_id = orders.order_id JOIN customers ON orders.customer_id = customers.customer_id;',
    result: 'Correct',
    responseTimeMs: 210,
    expectedAnswer: 'Performs a three-way join to match products to customer cities.',
    tablesUsed: ['order_items', 'products', 'orders', 'customers'],
    timestamp: '2026-06-26T15:38:00+07:00'
  },
  {
    id: 'bq-40',
    question: 'Show payment method, customer name, and order date.',
    expectedSql: 'SELECT payments.method, customers.name, orders.order_date FROM payments JOIN orders ON payments.order_id = orders.order_id JOIN customers ON orders.customer_id = customers.customer_id;',
    generatedSql: 'SELECT payments.method, customers.name, orders.order_date FROM payments JOIN orders ON payments.order_id = orders.order_id JOIN customers ON orders.customer_id = customers.customer_id;',
    result: 'Correct',
    responseTimeMs: 180,
    expectedAnswer: 'Performs a three-way join to match payments to buyer names.',
    tablesUsed: ['payments', 'orders', 'customers'],
    timestamp: '2026-06-26T15:39:00+07:00'
  },
  {
    id: 'bq-41',
    question: 'Find orders placed after June 20, 2026.',
    expectedSql: 'SELECT * FROM orders WHERE order_date > \'2026-06-20\';',
    generatedSql: 'SELECT * FROM orders WHERE order_date > \'2026-06-20\';',
    result: 'Correct',
    responseTimeMs: 90,
    expectedAnswer: 'Filters transactions by date threshold.',
    tablesUsed: ['orders'],
    timestamp: '2026-06-26T15:40:00+07:00'
  },
  {
    id: 'bq-42',
    question: 'List customers who registered before June 2023.',
    expectedSql: 'SELECT * FROM customers WHERE created_at < \'2023-06-01\';',
    generatedSql: 'SELECT * FROM customers WHERE created_at < \'2023-06-01\';',
    result: 'Correct',
    responseTimeMs: 80,
    expectedAnswer: 'Filters customer registration dates.',
    tablesUsed: ['customers'],
    timestamp: '2026-06-26T15:41:00+07:00'
  },
  {
    id: 'bq-43',
    question: 'Show payments processed on June 26, 2026.',
    expectedSql: 'SELECT * FROM payments WHERE paid_date = \'2026-06-26\';',
    generatedSql: 'SELECT * FROM payments WHERE paid_date = \'2026-06-26\';',
    result: 'Correct',
    responseTimeMs: 75,
    expectedAnswer: 'Filters payments by specific date.',
    tablesUsed: ['payments'],
    timestamp: '2026-06-26T15:42:00+07:00'
  },
  {
    id: 'bq-44',
    question: 'Show the top 3 most expensive products.',
    expectedSql: 'SELECT * FROM products ORDER BY unit_price DESC LIMIT 3;',
    generatedSql: 'SELECT * FROM products ORDER BY unit_price DESC LIMIT 3;',
    result: 'Correct',
    responseTimeMs: 72,
    expectedAnswer: 'Sorts products by price descending and limits to top 3.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:43:00+07:00'
  },
  {
    id: 'bq-45',
    question: 'Find the top 5 cities with the highest number of customers.',
    expectedSql: 'SELECT city, COUNT(*) AS cust_count FROM customers GROUP BY city ORDER BY cust_count DESC LIMIT 5;',
    generatedSql: 'SELECT city, COUNT(*) AS cust_count FROM customers GROUP BY city ORDER BY cust_count DESC LIMIT 5;',
    result: 'Correct',
    responseTimeMs: 115,
    expectedAnswer: 'Groups by city, counts customers, sorts descending with a limit of 5.',
    tablesUsed: ['customers'],
    timestamp: '2026-06-26T15:44:00+07:00'
  },
  {
    id: 'bq-46',
    question: 'Show the top 3 customers who spent the most.',
    expectedSql: 'SELECT name, SUM(order_total) AS spent FROM customers JOIN orders ON customers.customer_id = orders.customer_id GROUP BY name ORDER BY spent DESC LIMIT 3;',
    generatedSql: 'SELECT name, SUM(order_total) AS spent FROM customers JOIN orders ON customers.customer_id = orders.customer_id GROUP BY name ORDER BY spent DESC LIMIT 3;',
    result: 'Correct',
    responseTimeMs: 150,
    expectedAnswer: 'Joins, groups by name, sums order totals, sorts descending, limits to 3.',
    tablesUsed: ['customers', 'orders'],
    timestamp: '2026-06-26T15:45:00+07:00'
  },
  {
    id: 'bq-47',
    question: 'Show the profit margin for each product.',
    expectedSql: 'SELECT product_name, (unit_price - cost) AS margin FROM products;',
    generatedSql: 'SELECT product_name, (unit_price - cost) AS margin FROM products;',
    result: 'Correct',
    responseTimeMs: 65,
    expectedAnswer: 'Computes price minus cost for each product.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:46:00+07:00'
  },
  {
    id: 'bq-48',
    question: 'Calculate total revenue and total profit from all products sold.',
    expectedSql: 'SELECT SUM(line_total) AS total_revenue, SUM(line_total - (quantity * cost)) AS total_profit FROM order_items JOIN products ON order_items.product_id = products.product_id;',
    generatedSql: 'SELECT SUM(line_total) AS total_revenue, SUM(line_total - (quantity * cost)) AS total_profit FROM order_items JOIN products ON order_items.product_id = products.product_id;',
    result: 'Correct',
    responseTimeMs: 175,
    expectedAnswer: 'Joins tables and sums line totals and profit differences.',
    tablesUsed: ['order_items', 'products'],
    timestamp: '2026-06-26T15:47:00+07:00'
  },
  {
    id: 'bq-49',
    question: 'Show customer name and their average order total.',
    expectedSql: 'SELECT name, AVG(order_total) AS avg_total FROM customers JOIN orders ON customers.customer_id = orders.customer_id GROUP BY name;',
    generatedSql: 'SELECT name, AVG(order_total) AS avg_total FROM customers JOIN orders ON customers.customer_id = orders.customer_id GROUP BY name;',
    result: 'Correct',
    responseTimeMs: 128,
    expectedAnswer: 'Joins tables and calculates average order value grouped by buyer name.',
    tablesUsed: ['customers', 'orders'],
    timestamp: '2026-06-26T15:48:00+07:00'
  },
  {
    id: 'bq-50',
    question: 'Find the most popular product category by total quantity sold.',
    expectedSql: 'SELECT category, SUM(quantity) AS sold_qty FROM order_items JOIN products ON order_items.product_id = products.product_id GROUP BY category ORDER BY sold_qty DESC LIMIT 1;',
    generatedSql: 'SELECT category, SUM(quantity) AS sold_qty FROM order_items JOIN products ON order_items.product_id = products.product_id GROUP BY category ORDER BY sold_qty DESC LIMIT 1;',
    result: 'Correct',
    responseTimeMs: 162,
    expectedAnswer: 'Groups by category, sums quantities, sorts descending, and limits to 1.',
    tablesUsed: ['order_items', 'products'],
    timestamp: '2026-06-26T15:49:00+07:00'
  },
  {
    id: 'bq-51',
    question: 'What is the total count of orders with status refunded?',
    expectedSql: 'SELECT COUNT(*) FROM orders WHERE status = \'refunded\';',
    generatedSql: 'SELECT COUNT(*) FROM orders WHERE status = \'refunded\';',
    result: 'Correct',
    responseTimeMs: 50,
    expectedAnswer: 'Counts all orders with refunded status.',
    tablesUsed: ['orders'],
    timestamp: '2026-06-26T15:50:00+07:00'
  },
  {
    id: 'bq-52',
    question: 'List all products with unit price below 1 million.',
    expectedSql: 'SELECT * FROM products WHERE unit_price < 1000000;',
    generatedSql: 'SELECT * FROM products WHERE unit_price < 1000000;',
    result: 'Correct',
    responseTimeMs: 58,
    expectedAnswer: 'Filters products with unit price below 1 million.',
    tablesUsed: ['products'],
    timestamp: '2026-06-26T15:51:00+07:00'
  }
];

// 3. User Activity Summaries (8 entries)
export const initialUserActivities: UserActivity[] = [
  { id: 'u-1', name: 'Farhan Hanif', email: 'farhan.hanif@lapisai.com', totalQueries: 142, loginTime: '2026-06-26 08:30', lastActivity: '2026-06-26 20:10', successRate: 95.8 },
  { id: 'u-2', name: 'Siti Aminah', email: 'siti.aminah@lapisai.com', totalQueries: 98, loginTime: '2026-06-26 09:15', lastActivity: '2026-06-26 20:05', successRate: 98.0 },
  { id: 'u-3', name: 'Rian Hidayat', email: 'rian.hidayat@lapisai.com', totalQueries: 75, loginTime: '2026-06-26 10:00', lastActivity: '2026-06-26 20:01', successRate: 85.3 },
  { id: 'u-4', name: 'Lina Wijaya', email: 'lina.wijaya@lapisai.com', totalQueries: 112, loginTime: '2026-06-26 08:45', lastActivity: '2026-06-26 19:55', successRate: 97.3 },
  { id: 'u-5', name: 'Andi Wijaya', email: 'andi.wijaya@lapisai.com', totalQueries: 84, loginTime: '2026-06-26 09:30', lastActivity: '2026-06-26 19:48', successRate: 92.9 },
  { id: 'u-6', name: 'Gita Lestari', email: 'gita.lestari@lapisai.com', totalQueries: 48, loginTime: '2026-06-26 13:00', lastActivity: '2026-06-26 18:42', successRate: 79.2 },
  { id: 'u-7', name: 'Eko Prasetyo', email: 'eko.prasetyo@lapisai.com', totalQueries: 62, loginTime: '2026-06-26 09:00', lastActivity: '2026-06-26 17:40', successRate: 91.9 },
  { id: 'u-8', name: 'Dewi Sartika', email: 'dewi.sartika@lapisai.com', totalQueries: 28, loginTime: '2026-06-26 10:30', lastActivity: '2026-06-26 11:42', successRate: 100.0 }
];

// 4. Daily Query Volume Trend for Recharts (Last 15 days)
export const queryVolumeTrend: DailyQueryVolume[] = [
  { date: '06-12', queries: 45, successRate: 88 },
  { date: '06-13', queries: 52, successRate: 90 },
  { date: '06-14', queries: 38, successRate: 85 },
  { date: '06-15', queries: 60, successRate: 92 },
  { date: '06-16', queries: 72, successRate: 94 },
  { date: '06-17', queries: 68, successRate: 91 },
  { date: '06-18', queries: 50, successRate: 88 },
  { date: '06-19', queries: 85, successRate: 95 },
  { date: '06-20', queries: 92, successRate: 93 },
  { date: '06-21', queries: 40, successRate: 82 },
  { date: '06-22', queries: 78, successRate: 91 },
  { date: '06-23', queries: 98, successRate: 94 },
  { date: '06-24', queries: 110, successRate: 96 },
  { date: '06-25', queries: 125, successRate: 97 },
  { date: '06-26', queries: 135, successRate: 94 }
];

// 5. Benchmark Accuracy runs history for Recharts (Last 6 runs)
export const benchmarkAccuracyTrend: BenchmarkRunHistory[] = [
  { runId: 'run-1', timestamp: '2026-06-10 14:00', totalQuestions: 15, accuracy: 66.7, avgResponseTimeMs: 148 },
  { runId: 'run-2', timestamp: '2026-06-13 09:30', totalQuestions: 15, accuracy: 73.3, avgResponseTimeMs: 142 },
  { runId: 'run-3', timestamp: '2026-06-16 11:15', totalQuestions: 15, accuracy: 80.0, avgResponseTimeMs: 135 },
  { runId: 'run-4', timestamp: '2026-06-20 16:45', totalQuestions: 15, accuracy: 80.0, avgResponseTimeMs: 131 },
  { runId: 'run-5', timestamp: '2026-06-24 10:20', totalQuestions: 15, accuracy: 86.7, avgResponseTimeMs: 128 },
  { runId: 'run-6', timestamp: '2026-06-26 15:00', totalQuestions: 15, accuracy: 80.0, avgResponseTimeMs: 131 }
];

// Helper to simulate the AI SQL Generation model evaluation
export const evaluateQuestion = (
  _questionText: string,
  expectedSql: string
): { generatedSql: string; status: 'Correct' | 'Incorrect'; responseTime: number } => {
  const isCorrect = Math.random() > 0.15; // 85% success rate for simulation
  const delay = Math.round(50 + Math.random() * 150); // 50-200ms

  let generated = expectedSql;
  if (!isCorrect) {
    // Modify SQL slightly to make it wrong for simulation
    if (expectedSql.includes('ORDER BY')) {
      generated = expectedSql.replace(/ORDER BY .* (DESC|ASC)/gi, 'ORDER BY line_total ASC');
    } else if (expectedSql.includes('GROUP BY')) {
      generated = expectedSql.replace(/GROUP BY [a-zA-Z._]+/gi, 'GROUP BY product_id');
    } else if (expectedSql.includes('JOIN')) {
      generated = expectedSql.replace(/JOIN [a-zA-Z._]+/gi, 'JOIN order_items');
    } else {
      generated = expectedSql + ' -- error query';
    }
  }

  return {
    generatedSql: generated,
    status: isCorrect ? 'Correct' : 'Incorrect',
    responseTime: delay
  };
};

export interface MockProduct {
  product_id: number;
  product_name: string;
  category: string;
  unit_price: number;
  cost: number;
}

export interface MockCustomer {
  customer_id: number;
  name: string;
  city: string;
  tier: 'Bronze' | 'Silver' | 'Gold' | 'Platinum';
  created_at: string;
}

export interface MockOrder {
  order_id: number;
  customer_id: number;
  order_date: string;
  status: 'completed' | 'cancelled' | 'refunded';
  order_total: number;
}

export const initialProducts: MockProduct[] = [
  { product_id: 101, product_name: 'MacBook Pro 14" M3', category: 'Electronics', unit_price: 25999000, cost: 18500000 },
  { product_id: 102, product_name: 'iPad Air 5', category: 'Electronics', unit_price: 10999000, cost: 8200000 },
  { product_id: 103, product_name: 'iPhone 15 Pro Max', category: 'Electronics', unit_price: 19999000, cost: 15000000 },
  { product_id: 104, product_name: 'Leather Jacket Classic', category: 'Apparel', unit_price: 1250000, cost: 750000 },
  { product_id: 105, product_name: 'Running Shoes Elite', category: 'Apparel', unit_price: 1850000, cost: 1100000 },
  { product_id: 106, product_name: 'Office Chair Ergonomic', category: 'Home & Living', unit_price: 2450000, cost: 1550000 },
  { product_id: 107, product_name: 'Desk Organizer Premium', category: 'Home & Living', unit_price: 350000, cost: 200000 },
  { product_id: 108, product_name: 'Python Data Science Book', category: 'Books', unit_price: 450000, cost: 280000 },
  { product_id: 109, product_name: 'SQL Cookbook', category: 'Books', unit_price: 380000, cost: 240000 },
  { product_id: 110, product_name: 'Coffee Maker Espresso', category: 'Home & Living', unit_price: 3200000, cost: 2100000 }
];

export const initialCustomers: MockCustomer[] = [
  { customer_id: 1, name: 'Farhan Hanif', city: 'Jakarta', tier: 'Gold', created_at: '2023-04-15' },
  { customer_id: 2, name: 'Siti Aminah', city: 'Bandung', tier: 'Silver', created_at: '2023-06-20' },
  { customer_id: 3, name: 'Rian Hidayat', city: 'Surabaya', tier: 'Bronze', created_at: '2023-01-10' },
  { customer_id: 4, name: 'Lina Wijaya', city: 'Jakarta', tier: 'Gold', created_at: '2023-09-05' },
  { customer_id: 5, name: 'Andi Wijaya', city: 'Medan', tier: 'Silver', created_at: '2023-11-12' },
  { customer_id: 6, name: 'Gita Lestari', city: 'Yogyakarta', tier: 'Bronze', created_at: '2024-02-18' },
  { customer_id: 7, name: 'Eko Prasetyo', city: 'Semarang', tier: 'Gold', created_at: '2023-07-22' },
  { customer_id: 8, name: 'Dewi Sartika', city: 'Bandung', tier: 'Platinum', created_at: '2024-03-01' },
  { customer_id: 9, name: 'Hendra Setiawan', city: 'Bandung', tier: 'Gold', created_at: '2024-01-15' },
  { customer_id: 10, name: 'Sinta Nuriyah', city: 'Bandung', tier: 'Gold', created_at: '2024-04-10' }
];

export const initialOrders: MockOrder[] = [
  { order_id: 10001, customer_id: 1, order_date: '2026-06-15', status: 'completed', order_total: 25999000 },
  { order_id: 10002, customer_id: 2, order_date: '2026-06-18', status: 'completed', order_total: 10999000 },
  { order_id: 10003, customer_id: 3, order_date: '2026-06-20', status: 'completed', order_total: 1850000 },
  { order_id: 10004, customer_id: 4, order_date: '2026-06-21', status: 'completed', order_total: 1250000 },
  { order_id: 10005, customer_id: 5, order_date: '2026-06-22', status: 'completed', order_total: 2450500 },
  { order_id: 10006, customer_id: 6, order_date: '2026-06-23', status: 'cancelled', order_total: 380000 },
  { order_id: 10007, customer_id: 7, order_date: '2026-06-24', status: 'completed', order_total: 450000 },
  { order_id: 10008, customer_id: 8, order_date: '2026-06-25', status: 'completed', order_total: 3200000 },
  { order_id: 10009, customer_id: 1, order_date: '2026-06-26', status: 'completed', order_total: 28249000 },
  { order_id: 10010, customer_id: 2, order_date: '2026-06-26', status: 'completed', order_total: 19999000 }
];
