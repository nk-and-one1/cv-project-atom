-- Starter category taxonomy. Edit/extend in the Rules tab.
INSERT OR IGNORE INTO categories (id, parent_id, name) VALUES
    (1,  NULL, 'Food'),
    (2,  1,    'Groceries'),
    (3,  1,    'Restaurants'),
    (4,  1,    'Coffee'),
    (10, NULL, 'Transport'),
    (11, 10,   'Fuel'),
    (12, 10,   'Taxi'),
    (13, 10,   'Public transport'),
    (20, NULL, 'Housing'),
    (21, 20,   'Rent'),
    (22, 20,   'Utilities'),
    (30, NULL, 'Shopping'),
    (31, 30,   'Clothing'),
    (32, 30,   'Electronics'),
    (33, 30,   'Online'),
    (40, NULL, 'Entertainment'),
    (41, 40,   'Subscriptions'),
    (42, 40,   'Events'),
    (50, NULL, 'Health'),
    (51, 50,   'Pharmacy'),
    (52, 50,   'Medical'),
    (60, NULL, 'Income'),
    (61, 60,   'Salary'),
    (62, 60,   'Transfers in'),
    (70, NULL, 'Transfers'),
    (71, 70,   'Internal'),
    (72, 70,   'To others'),
    (99, NULL, 'Uncategorized');

-- Starter merchant rules (generic; safe to edit/remove in the Rules tab).
-- Matched case-insensitively against "merchant + description".
INSERT OR IGNORE INTO rules (pattern, category_id, priority) VALUES
    ('espresso|master ?coffee|\bcoffee\b|\bkofe|paris-brest|global coffee|coco kabanbay', 4, 50),
    ('\bazs\b|qazaq oil', 11, 50),
    ('yandex\.go|indriver|\bbolt\b', 12, 50),
    ('claude\.ai|apple\.com|itunes|spotify|netflix|subscription', 41, 50);
