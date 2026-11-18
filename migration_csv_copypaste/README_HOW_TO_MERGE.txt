CSV COPY-PASTE CHUNKS FOR MIGRATION
======================================================================
Max per part: 500000 characters (5 lakh). Split on full CSV rows.

HOW TO MERGE (other laptop)
----------------------------------------------------------------------
For each TARGET csv:
  1. Create the empty target .csv file in the correct folder
  2. Open part01 -> Select All -> Copy -> Paste into the csv
  3. Open part02 -> Select All -> Copy -> Paste at END of same csv
  4. Continue part03... in order
  5. Save

Rules:
  - Paste parts in order (01 then 02 then 03)
  - Do not insert blank lines between pastes
  - Only part01 has the header row

TARGET FILE: ML Project/editor_queue_urgency/dataset/synthetic_news.csv
  Full size: 1408974 chars | Split into 3 parts
  1. 01_editor_urgency_synthetic_news__part01_of_03.txt
     chars=499952  bytes=499952
  2. 01_editor_urgency_synthetic_news__part02_of_03.txt
     chars=499808  bytes=499808
  3. 01_editor_urgency_synthetic_news__part03_of_03.txt
     chars=409214  bytes=409214

TARGET FILE: ML Project/news_category/dataset/news_category.csv
  Full size: 1278745 chars | Split into 3 parts
  1. 02_news_category_topics__part01_of_03.txt
     chars=499834  bytes=503042
  2. 02_news_category_topics__part02_of_03.txt
     chars=499909  bytes=502388
  3. 02_news_category_topics__part03_of_03.txt
     chars=279002  bytes=280419

PASTE ORDER
----------------------------------------------------------------------
  01_editor_urgency_synthetic_news__part01_of_03.txt
  01_editor_urgency_synthetic_news__part02_of_03.txt
  01_editor_urgency_synthetic_news__part03_of_03.txt
  02_news_category_topics__part01_of_03.txt
  02_news_category_topics__part02_of_03.txt
  02_news_category_topics__part03_of_03.txt
