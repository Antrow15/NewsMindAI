-- Seed roles and categories for NewsMind console

INSERT INTO role (role_code, role_name, is_active) VALUES
    ('administrator', 'Administrator', TRUE),
    ('audience_insight_analyst', 'Audience Insight Analyst', TRUE),
    ('editor', 'Editor', TRUE),
    ('journalist', 'Journalist', TRUE),
    ('content_adaptation_editor', 'Content Adaptation Editor', TRUE),
    ('publisher', 'Publisher', TRUE),
    ('newsroom_manager', 'Newsroom Manager', TRUE)
ON CONFLICT (role_code) DO NOTHING;

INSERT INTO category (category_name, description, is_active) VALUES
    ('Politics', 'Political coverage (ML topic)', TRUE),
    ('Sports', 'Sports coverage (ML topic)', TRUE),
    ('Business', 'Business and markets (ML topic)', TRUE),
    ('Entertainment', 'Entertainment and culture (ML topic)', TRUE),
    ('World', 'World / international news (ML topic)', TRUE),
    ('City', 'City and civic news (manual desk label)', TRUE),
    ('Weather', 'Weather and climate (manual desk label)', TRUE)
ON CONFLICT (category_name) DO NOTHING;
