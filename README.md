# unit2_capstone
## Trust-but-Verify

Note: this project uses Gemini (`gemini-3.5-flash`) through `llm.py`, so "the model" below refers to Gemini.

### Test 1: Quantitative query

1. **Query submitted:** `Show me monthly revenue trends`
2. **What the model returned:** The manager routed it to the quantitative agent, which generated
   `SELECT strftime('%Y-%m', date) AS month, SUM(revenue) AS total_revenue FROM sales GROUP BY month ORDER BY month;`
   The explanation step then failed with a `429 RESOURCE_EXHAUSTED` error (Gemini free tier limit of 5 requests/minute).
3. **What the validation layer flagged:** `⚠️ VALIDATION WARNING: SQL validation status: ERROR`
4. **Accepted / changed / why:**
   - Accepted the SQL after reading it: it groups by month and sums revenue, which is correct for the question, and it passed `validate_sql` (SELECT only).
   - Changed `llm.py` to catch 429 errors, wait the retry time Gemini reports, and retry.
   - Reason: the warning said the query execution failed, but the failure was the rate limit on the explanation call, not the SQL.
   - After the fix I re-ran the query. [PASTE the re-run output, e.g. the monthly totals returned]
   - [PASTE: did the monthly totals match my direct SQLite check? Yes/No]

### Test 2: Quantitative query

1. **Query submitted:** `What is our customer churn rate?`

2. **What the model returned:** The manager routed the query to the quantitative agent. The model generated this SQL:
```sql
   SELECT CAST(COUNT(churn_date) AS REAL) / COUNT(*) AS churn_rate FROM customers;
```
   and answered: "The customer churn rate is **0.112** (or 11.2%)."

3. **What the validation layer flagged:** Nothing. `validate_sql` accepted the query (it starts with SELECT, contains no blocked keywords, and is a single statement), the execution status was PASSED, and no `VALIDATION WARNING` was printed.

4. **What I accepted, what I changed, and why:**
   - **Accepted** the answer, but only after verifying it independently. I ran this directly against the SQLite database:
```sql
     SELECT COUNT(*), SUM(churn_date IS NOT NULL) FROM customers
```
     The result was `(250, 28)`: 28 churned customers out of 250, which is 11.2% and matches the model's 0.112.
   - I also checked the SQL logic. `COUNT(churn_date)` ignores NULL values, so it counts only customers with a churn date, which is the correct numerator. `COUNT(*)` counts all customers, which is the correct denominator. `CAST(... AS REAL)` prevents SQLite's integer division from returning 0.
   - I ran both results with Claude to confirm and made these notes below. 
   - **Changed nothing** in the code for this query.
   - **One thing I noted:** this is customer-count churn. The customer success strategy document quotes 11.2% as revenue churn, which is a different measure. The two match here only because of how the dummy data was built. In a real system they would need to be reported separately.
   - **Tokenomics observation:** the quantitative call used 387 input tokens but 1,517 output tokens (about $0.014), far more output than a one-line SQL statement needs. Gemini's hidden "thinking" tokens are billed as output, so the real cost of a short answer is higher than its length suggests. I count them in `llm.py` so the log reflects true cost.
   - The console also showed an SDK notice about automatic function calling. It is informational, not an error, and I did not act on it.

### Test 3: Quantitative query that failed validation (the case I did not immediately trust)

1. **Query submitted:** `Compare Q4 performance across regions`

2. **What the model returned (first run):** The manager routed the query to the quantitative agent, but the "SQL" it returned was not a query. It was a fragment of the model's own reasoning that stopped mid-sentence:
```
   Wait, maybe just `SUM(revenue)` and `SUM(units_sold)` is enough for "performance". I will select `region`, `SUM(revenue)` as
```

3. **What the validation layer flagged:** `⚠️ VALIDATION WARNING: SQL validation status: FAILED`, with the message `Query blocked: Only SELECT queries are permitted`. `validate_sql` stopped the text before it reached the database, so nothing was executed.

4. **What I accepted, what I changed, and why:**
   - **Accepted** the validator's block. The output was not a valid query, so refusing it was correct.
   - **Diagnosed the cause** from the tokenomics line: the quantitative call used 1,020 output tokens against a `max_tokens` limit of 1,024 (the classifier call also came close, at 245 of 256). Gemini's hidden "thinking" tokens count toward that limit, so the model ran out of budget before it wrote the actual query, and the visible text was a truncated reasoning fragment.
   - **Changed** `llm.py` to use `max(max_tokens, 4096)` as the output limit, so thinking tokens no longer crowd out the answer.
   - **Re-ran** the same query. This time the model produced a valid query:
```sql
     SELECT region, SUM(revenue) AS total_revenue, SUM(units_sold) AS total_units_sold
     FROM sales
     WHERE strftime('%Y-%m', date) IN ('2025-10','2025-11', '2025-12')
     GROUP BY region ORDER BY total_revenue DESC;
```
     and answered with North America at $6,900,000 (8,105 units), EMEA at $4,100,000 (4,695 units), APAC at $2,400,000 (2,799 units), and LATAM at $800,000 (946 units). No validation warning was raised.
   - **Verified** the answer directly against SQLite with `SELECT region, SUM(revenue), SUM(units_sold) FROM sales WHERE strftime('%m', date) IN ('10','11','12') GROUP BY region ORDER BY 2 DESC`. The result matched the model's figures exactly, and the revenue totals add up to $14.2M, the Q4 total the database was seeded with.
   - **Noted the cost:** the re-run used 521 input and 1,998 output tokens (about $0.019) for the quantitative call. Most of that output is thinking tokens, so the higher limit made this query more expensive than the one-line SQL suggests.

5. **Why I did not trust this output, and how I resolved it:** The first failure looked like a model reasoning error, but the real cause was a token budget problem in my own wrapper code. The validator correctly blocked the output, yet it only said the query was not a SELECT. Reading the token counts is what revealed the true cause. Without validating the SQL before execution, the app would have tried to run a sentence as a database query. After raising the limit and re-running, I confirmed the answer against the database before accepting it.