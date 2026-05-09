Here's a breakdown of all 12 questions and how effectively the chatbot answered each:                                           
                                                 
  ---                                                                                                                             
  Q1: Show me the possible visa sponsoring roles in data analyst                                                                    Effective. Returned 3 specific roles from Deloitte with job descriptions, qualifications, and salary ranges. Correctly noted    
  that sponsorship is limited/conditional.                                                                                        

  ---
  Q2: Moving to New York, beginner DA, Python only — what roles are available?
  Partially effective. Correctly said no beginner NYC roles were found, but the fallback results weren't filtered by location and 
  ignored the Python-only constraint. Didn't tailor suggestions to the user's skill level.

  ---
  Q3: Managerial roles for remote
  Effective. Listed 5 relevant roles with descriptions, qualifications, and salaries. Minor issue: in the file, the answer appears
   before the question (ordering/rendering bug), but the content itself was solid.

  ---
  Q4: AI jobs with Python preferred
  Mostly effective. Returned 5 relevant roles. The last entry (JPMorgan Data Engineer III) was cut off mid-sentence — likely a    
  truncation bug.

  ---
  Q5: MSBA graduate — what roles fit?
  Weak. Started well with 3 relevant roles, but then appended unrelated content about beginner-level experience (lines 124–155)   
  that had nothing to do with the MSBA question. Looks like a context bleed from another query.

  ---
  Q6: Show me the image of Deloitte
  Acceptable. Correctly stated it couldn't retrieve images (expected limitation for a text-based system). Handled gracefully.     

  ---
  Q7: Company culture at JPMorgan Chase
  Effective. Gave a solid cultural overview covering diversity, benefits, career growth, and collaboration. Backed it up with a   
  relevant job posting as a real-world example.

  ---
  Q8: JP Morgan locations in USA
  Effective. Listed 5 specific cities with street addresses and associated job titles. Clean and informative.

  ---
  Q9: Highest level position at Deloitte
  Partially effective. Identified "Lead Data Expert" as the highest, but this is based only on what's in the job database — not   
  Deloitte's actual org hierarchy. Should have clarified that limitation upfront more explicitly.

  ---
  Q10: Salary for managerial roles in analyst area
  Effective. Returned 2 roles with clear salary ranges and relevant qualifications.

  ---
  Q11: Most needed skill for beginner level
  Not effective. Deflected by saying no beginner roles exist, then listed a senior consultant role. Never actually answered what  
  skills a beginner should focus on.

  ---
  Q12: How many years of experience for beginner level
  Partially effective. Couldn't find beginner roles directly but tried to infer from existing postings (minimum ~2 years from     
  Qualtrics role). Reasonable workaround, but repeated the same answer as Q11 verbatim — suggests no differentiation between      
  closely related questions.

  ---
  Overall Assessment

  ┌───────────────────────────────┬────────────────────────────────────────────────────────────────────────────┐
  │             Area              │                                   Result                                   │
  ├───────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ Job search / filtering        │ Good for specific queries, weak on multi-filter (location + skill + level) │
  ├───────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ Salary / location data        │ Strong                                                                     │
  ├───────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ Beginner-level questions      │ Consistently weak — no entry-level data in the DB                          │
  ├───────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ Context bleed (Q5)            │ Bug — unrelated content appended                                           │
  ├───────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ Truncation (Q4)               │ Bug — response cut off mid-sentence                                        │
  ├───────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ Out-of-scope queries (images) │ Handled appropriately                                                      │
  └───────────────────────────────┴────────────────────────────────────────────────────────────────────────────┘

  The chatbot performs well on direct lookup queries but struggles with nuanced, multi-criteria filters and beginner-oriented     
  questions where the database likely lacks entry-level postings.