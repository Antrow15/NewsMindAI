-- NewsMindAI V2 — temporary / probe desk data for local testing.
-- Prerequisite: python app.py --init-db  (roles + demo users must already exist)
--
-- Apply (recommended):
--   python -c "from pathlib import Path; from database.connection import apply_sql_file; apply_sql_file(Path('database/seed_temp_data.sql'))"
-- Or:
--   psql -h localhost -U postgres -d newsmind_console -f database/seed_temp_data.sql
--
-- Safe to re-run: deletes prior rows with these seed titles, then inserts fresh.
-- Does NOT create demo login users (see database/seed_demo_users.py).
--
-- NOTE: avoid DO $$ blocks — apply_sql_file splits on ';' and cannot run them.
-- Leave BEGIN/COMMIT out so database.connection.apply_sql_file wraps one transaction.
-- Published rows use source_type='desk' so related-content / TF-IDF can find them.

-- ---------------------------------------------------------------------------
-- Resolve desk IDs from demo usernames
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _seed_ids AS
SELECT
    (SELECT user_id FROM users WHERE username = 'journalist') AS journalist_user_id,
    (SELECT journalist_id FROM journalist j
        JOIN users u ON u.user_id = j.user_id
     WHERE u.username = 'journalist') AS journalist_id,
    (SELECT user_id FROM users WHERE username = 'analyst') AS analyst_user_id,
    (SELECT aia_id FROM audience_insight_analyst a
        JOIN users u ON u.user_id = a.user_id
     WHERE u.username = 'analyst') AS aia_id,
    (SELECT user_id FROM users WHERE username = 'editor') AS editor_user_id,
    (SELECT user_id FROM users WHERE username = 'manager') AS manager_user_id,
    (SELECT user_id FROM users WHERE username = 'publisher') AS publisher_user_id;

SELECT 1 / CASE WHEN journalist_id IS NULL THEN 0 ELSE 1 END AS journalist_ok
FROM _seed_ids;

SELECT 1 / CASE WHEN aia_id IS NULL THEN 0 ELSE 1 END AS analyst_ok
FROM _seed_ids;

-- ---------------------------------------------------------------------------
-- Extra categories
-- ---------------------------------------------------------------------------
INSERT INTO category (category_name, description, is_active) VALUES
    ('Transit', 'Transit and infrastructure', TRUE),
    ('Local', 'Local desk topics', TRUE),
    ('Health', 'Public health and hospitals', TRUE),
    ('Education', 'Schools and universities', TRUE),
    ('Technology', 'Tech and digital policy', TRUE)
ON CONFLICT (category_name) DO UPDATE
SET description = EXCLUDED.description,
    is_active = TRUE,
    updated_at = NOW();

-- ---------------------------------------------------------------------------
-- Title registry (cleanup + inserts share this list)
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _seed_titles (
    title VARCHAR(512) PRIMARY KEY
);

INSERT INTO _seed_titles (title) VALUES
    ('City council approves downtown metro expansion plan'),
    ('Metro expansion: what residents need to know'),
    ('Neighborhood groups seek metro construction noise limits'),
    ('Opinion roundup: was the metro vote rushed?'),
    ('University district prepares for metro station groundbreaking'),
    ('Manager reject sample: incomplete metro sidebar'),
    ('Transit levy debate heats up ahead of spring ballot'),
    ('Regional bank reports stronger Q3 earnings on lending growth'),
    ('Draft: waterfront festival schedule still incomplete'),
    ('Submitted: firefighters contain warehouse blaze on 4th Avenue'),
    ('Approved: city opens new overnight shelter downtown'),
    ('Published: heat advisory extended through Thursday'),
    ('Published: high school robotics team wins regional finals'),
    ('Published: port authority expands evening ferry service'),
    ('Rework: hospital reports rising ER wait times'),
    ('Rejected: unverified tip about mayoral resignation'),
    ('Submitted: teachers union sets strike authorization vote'),
    ('Published: startup raises Series B for climate sensors'),
    ('Draft: interview notes from climate summit day one'),
    ('Approved: photo essay on river cleanup volunteers'),
    ('Published: sports desk preview — derby match weekend'),
    ('Submitted: cybersecurity alert for city vendor portal'),
    ('Published: film festival announces opening-night lineup'),
    ('Rework: investigation into school lunch contract delays');

CREATE TEMP TABLE _seed_pitch_titles (
    title VARCHAR(512) PRIMARY KEY
);

INSERT INTO _seed_pitch_titles (title) VALUES
    ('Who benefits from the metro expansion?'),
    ('Fare policy after metro expansion'),
    ('Small businesses near future metro stations'),
    ('Unused pitch for manager reject demo'),
    ('Youth sports funding after stadium upgrades'),
    ('Hospital staffing gaps ahead of flu season'),
    ('Ferry expansion and waterfront rent pressure'),
    ('Climate sensors: civic use cases worth covering'),
    ('Teacher strike authorization — what parents need'),
    ('Thin tip: celebrity rumor not worth assignment');

-- ---------------------------------------------------------------------------
-- Clear previous seed rows
-- ---------------------------------------------------------------------------
DELETE FROM publication
WHERE content_id IN (
    SELECT c.content_id FROM content c
    JOIN _seed_titles t ON t.title = c.title
);

DELETE FROM content
WHERE title IN (SELECT title FROM _seed_titles);

DELETE FROM story_pitch
WHERE title IN (SELECT title FROM _seed_pitch_titles);

-- ===========================================================================
-- ORIGINAL METRO CLUSTER (relevancy / credibility / publisher)
-- ===========================================================================

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version,
        submitted_at, approved_at, published_at
    )
    SELECT
        j.journalist_id,
        'City council approves downtown metro expansion plan',
        'Council votes 7-2 to fund phase one of the metro line.',
        'The city council approved a multi-year metro expansion after public hearings. Phase one connects downtown to the university district. Funding includes state grants and a local transit levy. Construction may begin next spring if permits clear on schedule.',
        'The city council approved a multi-year metro expansion after public hearings. Phase one connects downtown to the university district. Funding includes state grants and a local transit levy. Construction may begin next spring if permits clear on schedule.',
        'news', 'desk', 'published', 1,
        NOW() - INTERVAL '3 days', NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day'
    FROM j
    RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Metro expansion vote', 'city', 'City Hall', FALSE, 'medium' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Council vote minutes — metro expansion', 'link',
       'https://example.com/council/minutes/metro-2026',
       'Motion to approve phase-one metro funding passed 7-2.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'City council approves downtown metro expansion plan';

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'State grant award letter', 'document',
       'https://example.com/grants/metro',
       'State awarded matching funds for phase-one construction.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'City council approves downtown metro expansion plan';

INSERT INTO publication (content_id, template_code, status, published_at)
SELECT c.content_id, 'web_standard', 'published', c.published_at
FROM content c WHERE c.title = 'City council approves downtown metro expansion plan';

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version,
        submitted_at, approved_at, published_at
    )
    SELECT
        j.journalist_id,
        'Metro expansion: what residents need to know',
        'Timeline, funding, and neighborhood impacts of the approved metro plan.',
        'Residents near the planned stations will see temporary road closures. Officials say ridership projections justify the investment. Opposition groups cite cost overruns on prior transit projects across the region.',
        'Residents near the planned stations will see temporary road closures. Officials say ridership projections justify the investment. Opposition groups cite cost overruns on prior transit projects across the region.',
        'article', 'desk', 'published', 1,
        NOW() - INTERVAL '3 days', NOW() - INTERVAL '2 days', NOW() - INTERVAL '12 hours'
    FROM j
    RETURNING content_id
)
INSERT INTO article (content_id, article_type, estimated_read_time)
SELECT content_id, 'feature', 4 FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Transit agency brief', 'document',
       'https://example.com/transit/brief',
       'Phase one timeline and station list confirmed.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Metro expansion: what residents need to know';

INSERT INTO publication (content_id, template_code, status, scheduled_at)
SELECT c.content_id, 'newsletter', 'scheduled', NOW() + INTERVAL '2 days'
FROM content c WHERE c.title = 'Metro expansion: what residents need to know';

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, published_at
    )
    SELECT j.journalist_id,
        'Transit levy debate heats up ahead of spring ballot',
        'Advocates and critics clash over metro funding levy.',
        'Voters will decide whether to extend the transit levy that backs metro construction. Business groups support faster downtown access while neighbors worry about displacement.',
        'Voters will decide whether to extend the transit levy that backs metro construction. Business groups support faster downtown access while neighbors worry about displacement.',
        'news', 'desk', 'published', 1, NOW() - INTERVAL '6 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Transit levy debate', 'city', 'Downtown', FALSE, 'low' FROM ins;

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, published_at
    )
    SELECT j.journalist_id,
        'Regional bank reports stronger Q3 earnings on lending growth',
        'Local lenders cite commercial real estate recovery.',
        'A regional bank posted higher quarterly earnings, pointing to commercial lending. Mortgage demand remains soft according to analysts.',
        'A regional bank posted higher quarterly earnings, pointing to commercial lending. Mortgage demand remains soft according to analysts.',
        'news', 'desk', 'published', 1, NOW() - INTERVAL '8 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Bank Q3 earnings', 'business', 'Financial district', FALSE, 'low' FROM ins;

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, submitted_at
    )
    SELECT j.journalist_id,
        'Neighborhood groups seek metro construction noise limits',
        'Residents push for overnight noise limits during tunneling.',
        'Neighborhood associations asked the council to cap overnight construction noise during metro tunneling. Officials said mitigation plans are under review and will be published before excavation begins near residential blocks.',
        'Neighborhood associations asked the council to cap overnight construction noise during metro tunneling. Officials said mitigation plans are under review and will be published before excavation begins near residential blocks.',
        'news', 'desk', 'rework', 1, NOW() - INTERVAL '1 day'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Construction noise limits', 'city', 'University district', FALSE, 'medium' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Neighborhood petition', 'document',
       'https://example.com/petition/noise',
       '1200 signatures calling for overnight work limits.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Neighborhood groups seek metro construction noise limits';

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, submitted_at
    )
    SELECT j.journalist_id,
        'Opinion roundup: was the metro vote rushed?',
        'Local columns clash over metro vote process.',
        'Columnists disagree on whether the council had enough public comment before approving metro funding. Several argued hearings were truncated while others said the project has been studied for years.',
        'Columnists disagree on whether the council had enough public comment before approving metro funding. Several argued hearings were truncated while others said the project has been studied for years.',
        'article', 'desk', 'rejected', 1, NOW() - INTERVAL '2 days'
    FROM j RETURNING content_id
)
INSERT INTO article (content_id, article_type, estimated_read_time)
SELECT content_id, 'opinion', 3 FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Op-ed clip', 'link',
       'https://example.com/opeds/metro',
       'Editors collected three contrasting columns.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Opinion roundup: was the metro vote rushed?';

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version,
        submitted_at, approved_at
    )
    SELECT j.journalist_id,
        'University district prepares for metro station groundbreaking',
        'Campus adjusts mobility plans before metro groundbreaking.',
        'Campus planners outlined shuttle changes and bike parking expansions ahead of the university-district metro groundbreaking. Student groups asked for clearer construction timelines before finals week.',
        'Campus planners outlined shuttle changes and bike parking expansions ahead of the university-district metro groundbreaking. Student groups asked for clearer construction timelines before finals week.',
        'news', 'desk', 'approved', 1,
        NOW() - INTERVAL '20 hours', NOW() - INTERVAL '10 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Campus metro groundbreaking', 'city', 'University district', FALSE, 'low' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Campus planning memo', 'document',
       'https://example.com/campus/metro',
       'Shuttle reroutes proposed for groundbreaking week.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'University district prepares for metro station groundbreaking';

INSERT INTO publication (content_id, template_code, status)
SELECT c.content_id, 'web_standard', 'ready'
FROM content c WHERE c.title = 'University district prepares for metro station groundbreaking';

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, submitted_at
    )
    SELECT j.journalist_id,
        'Manager reject sample: incomplete metro sidebar',
        'Incomplete sidebar held for sourcing.',
        'Draft sidebar lacks confirmed quotes from transit officials and should not move. Holding for sourcing before any further desk action on this incomplete piece.',
        'Draft sidebar lacks confirmed quotes from transit officials and should not move. Holding for sourcing before any further desk action on this incomplete piece.',
        'news', 'desk', 'rejected', 1, NOW() - INTERVAL '5 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Incomplete sidebar', 'city', 'Newsroom', FALSE, 'low' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Internal note', 'document', '',
       'Missing official comment.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Manager reject sample: incomplete metro sidebar';

-- ===========================================================================
-- EXTRA DESK ITEMS (more statuses / topics for queue testing)
-- ===========================================================================

-- Draft
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version
    )
    SELECT j.journalist_id,
        'Draft: waterfront festival schedule still incomplete',
        'Organizers have not finalized weekend stage times.',
        'The waterfront festival committee released a partial schedule but left Saturday headliners blank. Vendors say they need confirmation before ordering inventory for the three-day event.',
        'The waterfront festival committee released a partial schedule but left Saturday headliners blank. Vendors say they need confirmation before ordering inventory for the three-day event.',
        'article', 'desk', 'draft', 1
    FROM j RETURNING content_id
)
INSERT INTO article (content_id, article_type, estimated_read_time)
SELECT content_id, 'preview', 2 FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Festival committee email', 'document',
       'https://example.com/festival/schedule-draft',
       'Saturday headliners TBD as of Monday morning.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Draft: waterfront festival schedule still incomplete';

-- Draft interview notes
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version
    )
    SELECT j.journalist_id,
        'Draft: interview notes from climate summit day one',
        'Raw notes pending cleanup and fact checks.',
        'Day-one panels focused on coastal flooding models and insurance pricing. Two mayors disagreed on whether state matching funds will arrive before hurricane season. Quotes need attribution cleanup before filing.',
        'Day-one panels focused on coastal flooding models and insurance pricing. Two mayors disagreed on whether state matching funds will arrive before hurricane season. Quotes need attribution cleanup before filing.',
        'article', 'desk', 'draft', 1
    FROM j RETURNING content_id
)
INSERT INTO article (content_id, article_type, estimated_read_time)
SELECT content_id, 'notes', 5 FROM ins;

-- Submitted breaking-ish news
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, submitted_at
    )
    SELECT j.journalist_id,
        'Submitted: firefighters contain warehouse blaze on 4th Avenue',
        'No injuries reported after overnight fire near the port.',
        'Firefighters contained a warehouse blaze on 4th Avenue after a three-hour response. Officials said the cause remains under investigation and nearby businesses reopened by mid-morning. Traffic diversions stayed in place through the lunch hour.',
        'Firefighters contained a warehouse blaze on 4th Avenue after a three-hour response. Officials said the cause remains under investigation and nearby businesses reopened by mid-morning. Traffic diversions stayed in place through the lunch hour.',
        'news', 'desk', 'submitted', 1, NOW() - INTERVAL '3 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Warehouse fire', 'emergency', '4th Avenue', TRUE, 'high' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Fire department incident log', 'document',
       'https://example.com/fd/incident/4th-ave',
       'Contained at 05:40. No civilian injuries.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Submitted: firefighters contain warehouse blaze on 4th Avenue';

-- Submitted education
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, submitted_at
    )
    SELECT j.journalist_id,
        'Submitted: teachers union sets strike authorization vote',
        'Members will vote next week on authorizing a strike.',
        'The teachers union scheduled a strike authorization vote after contract talks stalled on class size and healthcare contributions. District officials said classrooms will remain open while negotiations continue under a state mediator.',
        'The teachers union scheduled a strike authorization vote after contract talks stalled on class size and healthcare contributions. District officials said classrooms will remain open while negotiations continue under a state mediator.',
        'news', 'desk', 'submitted', 1, NOW() - INTERVAL '9 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Teacher strike vote', 'education', 'District HQ', FALSE, 'medium' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Union bargaining update', 'link',
       'https://example.com/union/bargaining',
       'Authorization vote set for next Tuesday evening.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Submitted: teachers union sets strike authorization vote';

-- Submitted tech
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, submitted_at
    )
    SELECT j.journalist_id,
        'Submitted: cybersecurity alert for city vendor portal',
        'IT desk urges password resets after suspicious logins.',
        'The city IT department issued a cybersecurity alert after detecting suspicious logins on a vendor payment portal. Contractors were told to reset passwords and enable multi-factor authentication before submitting invoices this week.',
        'The city IT department issued a cybersecurity alert after detecting suspicious logins on a vendor payment portal. Contractors were told to reset passwords and enable multi-factor authentication before submitting invoices this week.',
        'news', 'desk', 'submitted', 1, NOW() - INTERVAL '2 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Vendor portal alert', 'technology', 'City IT', FALSE, 'high' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'City IT advisory', 'link',
       'https://example.com/it/advisory/vendor-portal',
       'Reset credentials and enable MFA within 24 hours.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Submitted: cybersecurity alert for city vendor portal';

-- Approved shelter
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version,
        submitted_at, approved_at
    )
    SELECT j.journalist_id,
        'Approved: city opens new overnight shelter downtown',
        '80-bed shelter opens ahead of cold-weather season.',
        'The city opened an 80-bed overnight shelter downtown after community groups pressed for more cold-weather capacity. Intake begins at 6 p.m. and includes caseworker referrals for housing and medical services.',
        'The city opened an 80-bed overnight shelter downtown after community groups pressed for more cold-weather capacity. Intake begins at 6 p.m. and includes caseworker referrals for housing and medical services.',
        'news', 'desk', 'approved', 1,
        NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Overnight shelter opening', 'city', 'Downtown', FALSE, 'medium' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Shelter opening press note', 'document',
       'https://example.com/housing/shelter-open',
       '80 beds. Intake 6 p.m. Caseworker referrals available.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Approved: city opens new overnight shelter downtown';

INSERT INTO publication (content_id, template_code, status)
SELECT c.content_id, 'print_column', 'ready'
FROM content c WHERE c.title = 'Approved: city opens new overnight shelter downtown';

-- Approved photo essay
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version,
        submitted_at, approved_at
    )
    SELECT j.journalist_id,
        'Approved: photo essay on river cleanup volunteers',
        'Weekend volunteers remove plastics from the riverbank.',
        'Volunteers filled dozens of bags with plastics during a weekend river cleanup. Organizers said participation doubled from last year and plan monthly events through spring with school clubs joining the effort.',
        'Volunteers filled dozens of bags with plastics during a weekend river cleanup. Organizers said participation doubled from last year and plan monthly events through spring with school clubs joining the effort.',
        'article', 'desk', 'approved', 1,
        NOW() - INTERVAL '30 hours', NOW() - INTERVAL '18 hours'
    FROM j RETURNING content_id
)
INSERT INTO article (content_id, article_type, estimated_read_time)
SELECT content_id, 'photo_essay', 3 FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Cleanup volunteer tally', 'document',
       'https://example.com/river/cleanup-tally',
       '142 volunteers. 68 bags of plastics collected.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Approved: photo essay on river cleanup volunteers';

-- More published (relevancy corpus richness)
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, published_at
    )
    SELECT j.journalist_id,
        'Published: heat advisory extended through Thursday',
        'National Weather Service extends heat advisory citywide.',
        'The National Weather Service extended a heat advisory through Thursday as temperatures stay above seasonal norms. Health officials urged residents to check on elderly neighbors and limit outdoor work during peak afternoon hours.',
        'The National Weather Service extended a heat advisory through Thursday as temperatures stay above seasonal norms. Health officials urged residents to check on elderly neighbors and limit outdoor work during peak afternoon hours.',
        'news', 'desk', 'published', 1, NOW() - INTERVAL '4 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Heat advisory', 'weather', 'Citywide', FALSE, 'medium' FROM ins;

INSERT INTO publication (content_id, template_code, status, published_at)
SELECT c.content_id, 'web_standard', 'published', c.published_at
FROM content c WHERE c.title = 'Published: heat advisory extended through Thursday';

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, published_at
    )
    SELECT j.journalist_id,
        'Published: high school robotics team wins regional finals',
        'Local team advances to state robotics championship.',
        'A local high school robotics team won regional finals after a late scoring push. Coaches credited after-school shop time and a redesigned drive train that held up through three elimination rounds.',
        'A local high school robotics team won regional finals after a late scoring push. Coaches credited after-school shop time and a redesigned drive train that held up through three elimination rounds.',
        'news', 'desk', 'published', 1, NOW() - INTERVAL '1 day'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Robotics finals', 'education', 'Convention Center', FALSE, 'low' FROM ins;

INSERT INTO publication (content_id, template_code, status, published_at)
SELECT c.content_id, 'social_short', 'published', c.published_at
FROM content c WHERE c.title = 'Published: high school robotics team wins regional finals';

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, published_at
    )
    SELECT j.journalist_id,
        'Published: port authority expands evening ferry service',
        'Extra evening sailings start next month for commuters.',
        'The port authority will expand evening ferry service next month with two additional sailings on weeknights. Officials said ridership surveys showed demand from late-shift workers and waterfront events.',
        'The port authority will expand evening ferry service next month with two additional sailings on weeknights. Officials said ridership surveys showed demand from late-shift workers and waterfront events.',
        'news', 'desk', 'published', 1, NOW() - INTERVAL '14 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Ferry expansion', 'transit', 'Waterfront', FALSE, 'low' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Port authority schedule release', 'link',
       'https://example.com/port/ferry-evening',
       'Two extra weeknight sailings begin next month.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Published: port authority expands evening ferry service';

INSERT INTO publication (content_id, template_code, status, published_at)
SELECT c.content_id, 'web_standard', 'published', c.published_at
FROM content c WHERE c.title = 'Published: port authority expands evening ferry service';

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, published_at
    )
    SELECT j.journalist_id,
        'Published: startup raises Series B for climate sensors',
        'Local climate-tech firm closes funding round.',
        'A local startup raised a Series B round to expand production of low-cost climate sensors used by cities to monitor heat islands. Investors said municipal contracts drove the valuation after pilot programs downtown.',
        'A local startup raised a Series B round to expand production of low-cost climate sensors used by cities to monitor heat islands. Investors said municipal contracts drove the valuation after pilot programs downtown.',
        'news', 'desk', 'published', 1, NOW() - INTERVAL '2 days'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Climate startup funding', 'business', 'Innovation district', FALSE, 'low' FROM ins;

INSERT INTO publication (content_id, template_code, status, published_at)
SELECT c.content_id, 'newsletter', 'published', c.published_at
FROM content c WHERE c.title = 'Published: startup raises Series B for climate sensors';

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, published_at
    )
    SELECT j.journalist_id,
        'Published: sports desk preview — derby match weekend',
        'Local clubs prepare for sold-out derby weekend.',
        'Both local clubs enter derby weekend with thin defensive lines after midweek injuries. Coaches said ticket demand forced an early gate opening and extra transit shuttles from downtown lots.',
        'Both local clubs enter derby weekend with thin defensive lines after midweek injuries. Coaches said ticket demand forced an early gate opening and extra transit shuttles from downtown lots.',
        'article', 'desk', 'published', 1, NOW() - INTERVAL '20 hours'
    FROM j RETURNING content_id
)
INSERT INTO article (content_id, article_type, estimated_read_time)
SELECT content_id, 'sports_preview', 4 FROM ins;

INSERT INTO publication (content_id, template_code, status, published_at)
SELECT c.content_id, 'print_column', 'published', c.published_at
FROM content c WHERE c.title = 'Published: sports desk preview — derby match weekend';

WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, published_at
    )
    SELECT j.journalist_id,
        'Published: film festival announces opening-night lineup',
        'Documentary slate leads opening night downtown.',
        'The film festival announced an opening-night lineup led by three documentaries on housing, climate migration, and local music history. Organizers expect sellouts and added a standby queue for student ticket holders.',
        'The film festival announced an opening-night lineup led by three documentaries on housing, climate migration, and local music history. Organizers expect sellouts and added a standby queue for student ticket holders.',
        'article', 'desk', 'published', 1, NOW() - INTERVAL '3 days'
    FROM j RETURNING content_id
)
INSERT INTO article (content_id, article_type, estimated_read_time)
SELECT content_id, 'arts', 3 FROM ins;

INSERT INTO publication (content_id, template_code, status, published_at)
SELECT c.content_id, 'web_standard', 'published', c.published_at
FROM content c WHERE c.title = 'Published: film festival announces opening-night lineup';

-- Rework health
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, submitted_at
    )
    SELECT j.journalist_id,
        'Rework: hospital reports rising ER wait times',
        'Needs clearer data tables and hospital response.',
        'Hospital administrators reported rising emergency-room wait times over the past quarter. Nurses cited staffing shortages while executives pointed to higher ambulance arrivals after clinic closures in outer neighborhoods.',
        'Hospital administrators reported rising emergency-room wait times over the past quarter. Nurses cited staffing shortages while executives pointed to higher ambulance arrivals after clinic closures in outer neighborhoods.',
        'news', 'desk', 'rework', 1, NOW() - INTERVAL '15 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'ER wait times', 'health', 'General Hospital', FALSE, 'medium' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Hospital quarterly dashboard', 'document',
       'https://example.com/hospital/er-waits',
       'Median ER wait rose from 42 to 61 minutes.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Rework: hospital reports rising ER wait times';

-- Rework education investigation
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, submitted_at
    )
    SELECT j.journalist_id,
        'Rework: investigation into school lunch contract delays',
        'Editor asked for vendor invoices and board minutes.',
        'A school lunch contract renewal has slipped three months, leaving kitchens short on staples. Board members blamed procurement software delays while parents said students are seeing smaller portions more often.',
        'A school lunch contract renewal has slipped three months, leaving kitchens short on staples. Board members blamed procurement software delays while parents said students are seeing smaller portions more often.',
        'article', 'desk', 'rework', 1, NOW() - INTERVAL '40 hours'
    FROM j RETURNING content_id
)
INSERT INTO article (content_id, article_type, estimated_read_time)
SELECT content_id, 'investigation', 8 FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Board procurement memo', 'document',
       'https://example.com/schools/lunch-contract',
       'Renewal delayed pending software migration.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Rework: investigation into school lunch contract delays';

-- Rejected thin tip
WITH j AS (SELECT journalist_id FROM _seed_ids),
ins AS (
    INSERT INTO content (
        author_id, title, summary, raw_body, content_body,
        content_kind, source_type, status, current_version, submitted_at
    )
    SELECT j.journalist_id,
        'Rejected: unverified tip about mayoral resignation',
        'No corroboration from city hall sources.',
        'An anonymous tip claimed the mayor planned to resign this week. City hall declined comment and no scheduling changes appeared on the public calendar. Desk rejected the item pending corroboration from two independent sources.',
        'An anonymous tip claimed the mayor planned to resign this week. City hall declined comment and no scheduling changes appeared on the public calendar. Desk rejected the item pending corroboration from two independent sources.',
        'news', 'desk', 'rejected', 1, NOW() - INTERVAL '6 hours'
    FROM j RETURNING content_id
)
INSERT INTO news (content_id, event_title, event_type, event_location, breaking_news_flag, severity)
SELECT content_id, 'Unverified resignation tip', 'politics', 'City Hall', FALSE, 'low' FROM ins;

INSERT INTO evidence (content_id, title, evidence_type, source_url, ocr_text, uploaded_by)
SELECT c.content_id, 'Anonymous tip note', 'document', '',
       'Single anonymous tip. No second source.',
       (SELECT journalist_id FROM _seed_ids)
FROM content c WHERE c.title = 'Rejected: unverified tip about mayoral resignation';

-- ===========================================================================
-- STORY PITCHES (AIA)
-- ===========================================================================
INSERT INTO story_pitch (
    audience_insight_id, title, summary, priority, source_type,
    trend_score, audience_interest_score, coverage_gap_score,
    status, created_by, approved_by, submitted_at, approved_at
)
SELECT s.aia_id,
    'Who benefits from the metro expansion?',
    'Equity analysis of station placement, fare policy, and neighborhood impact.',
    'high', 'aia', 72, 68, 45, 'approved',
    s.analyst_user_id, s.editor_user_id,
    NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day'
FROM _seed_ids s;

INSERT INTO story_pitch (
    audience_insight_id, title, summary, priority, source_type,
    trend_score, audience_interest_score, coverage_gap_score,
    status, created_by, submitted_at
)
SELECT s.aia_id,
    'Fare policy after metro expansion',
    'How new stations may change fare zones and transfer rules citywide.',
    'medium', 'aia', 60, 55, 50, 'rejected',
    s.analyst_user_id, NOW() - INTERVAL '2 days'
FROM _seed_ids s;

INSERT INTO story_pitch (
    audience_insight_id, title, summary, priority, source_type,
    trend_score, audience_interest_score, coverage_gap_score,
    status, created_by, approved_by, submitted_at, approved_at
)
SELECT s.aia_id,
    'Small businesses near future metro stations',
    'How retail corridors expect foot traffic to change after phase one opens.',
    'medium', 'aia', 58, 62, 40, 'approved',
    s.analyst_user_id, s.manager_user_id,
    NOW() - INTERVAL '1 day', NOW() - INTERVAL '12 hours'
FROM _seed_ids s;

INSERT INTO story_pitch (
    audience_insight_id, title, summary, priority, source_type,
    trend_score, audience_interest_score, coverage_gap_score,
    status, created_by, submitted_at
)
SELECT s.aia_id,
    'Unused pitch for manager reject demo',
    'Placeholder pitch created only so manager reject can be exercised safely.',
    'low', 'aia', 20, 20, 10, 'rejected',
    s.analyst_user_id, NOW() - INTERVAL '1 day'
FROM _seed_ids s;

INSERT INTO story_pitch (
    audience_insight_id, title, summary, priority, source_type,
    trend_score, audience_interest_score, coverage_gap_score,
    status, created_by, submitted_at
)
SELECT s.aia_id,
    'Youth sports funding after stadium upgrades',
    'Follow the money from stadium renovations into neighborhood youth leagues.',
    'high', 'aia', 66, 70, 48, 'submitted',
    s.analyst_user_id, NOW() - INTERVAL '8 hours'
FROM _seed_ids s;

INSERT INTO story_pitch (
    audience_insight_id, title, summary, priority, source_type,
    trend_score, audience_interest_score, coverage_gap_score,
    status, created_by, submitted_at
)
SELECT s.aia_id,
    'Hospital staffing gaps ahead of flu season',
    'Map nurse vacancies against projected winter ER demand.',
    'high', 'aia', 74, 71, 55, 'submitted',
    s.analyst_user_id, NOW() - INTERVAL '5 hours'
FROM _seed_ids s;

INSERT INTO story_pitch (
    audience_insight_id, title, summary, priority, source_type,
    trend_score, audience_interest_score, coverage_gap_score,
    status, created_by, approved_by, submitted_at, approved_at
)
SELECT s.aia_id,
    'Ferry expansion and waterfront rent pressure',
    'Does more evening ferry service accelerate rent spikes near terminals?',
    'medium', 'aia', 61, 64, 52, 'approved',
    s.analyst_user_id, s.editor_user_id,
    NOW() - INTERVAL '3 days', NOW() - INTERVAL '2 days'
FROM _seed_ids s;

INSERT INTO story_pitch (
    audience_insight_id, title, summary, priority, source_type,
    trend_score, audience_interest_score, coverage_gap_score,
    status, created_by, submitted_at
)
SELECT s.aia_id,
    'Climate sensors: civic use cases worth covering',
    'Where city heat-island sensors are installed and who reads the data.',
    'medium', 'aia', 57, 59, 44, 'submitted',
    s.analyst_user_id, NOW() - INTERVAL '11 hours'
FROM _seed_ids s;

INSERT INTO story_pitch (
    audience_insight_id, title, summary, priority, source_type,
    trend_score, audience_interest_score, coverage_gap_score,
    status, created_by, submitted_at
)
SELECT s.aia_id,
    'Teacher strike authorization — what parents need',
    'Explain voting timeline, possible walkout dates, and daycare fallout.',
    'high', 'aia', 69, 73, 41, 'submitted',
    s.analyst_user_id, NOW() - INTERVAL '4 hours'
FROM _seed_ids s;

INSERT INTO story_pitch (
    audience_insight_id, title, summary, priority, source_type,
    trend_score, audience_interest_score, coverage_gap_score,
    status, created_by, submitted_at
)
SELECT s.aia_id,
    'Thin tip: celebrity rumor not worth assignment',
    'Single social post with no local angle or confirmation.',
    'low', 'aia', 12, 15, 5, 'rejected',
    s.analyst_user_id, NOW() - INTERVAL '7 hours'
FROM _seed_ids s;
