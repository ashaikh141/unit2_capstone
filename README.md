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

### Test 3: Qualitative or multi-agent query

1. **Query submitted:** [e.g. `What is our company's security policy?`]
2. **What the model returned:** [PASTE the answer]
3. **What the validation layer flagged:** [PASTE the sources cited line and any warning]
4. **Accepted / changed / why:** [Open one of the cited .txt files and check that the claim really appears there. Write what you checked.]

### Case I did not immediately trust

[Describe the one case, the exact output that made you doubt it, how you checked it, and what you decided or changed.]