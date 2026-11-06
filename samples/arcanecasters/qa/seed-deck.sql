BEGIN;

SELECT 1 AS qa_bot_ready
FROM bot_personas AS bot
JOIN users ON users.id = bot.user_id
WHERE bot.user_id = :'bot_id' AND bot.enabled
  AND EXISTS (SELECT 1 FROM deck_cards WHERE deck_id = users.selected_deck_id)
\gset

INSERT INTO users (id) VALUES (:'account_id') ON CONFLICT (id) DO NOTHING;

WITH starter AS (
    INSERT INTO decks (name, user_id)
    SELECT 'QA starter', id FROM users WHERE id = :'account_id' AND selected_deck_id IS NULL
    RETURNING id, user_id
)
UPDATE users SET selected_deck_id = starter.id FROM starter WHERE users.id = starter.user_id;

INSERT INTO deck_cards (deck_id, magic_id, count)
SELECT player.selected_deck_id, cards.magic_id, cards.count
FROM users AS player
JOIN users AS bot ON bot.id = :'bot_id'
JOIN deck_cards AS cards ON cards.deck_id = bot.selected_deck_id
WHERE player.id = :'account_id'
  AND NOT EXISTS (SELECT 1 FROM deck_cards WHERE deck_id = player.selected_deck_id)
ON CONFLICT (magic_id, deck_id) DO NOTHING;

INSERT INTO user_magics (user_id, magic_id, count)
SELECT player.id, cards.magic_id, cards.count
FROM users AS player
JOIN deck_cards AS cards ON cards.deck_id = player.selected_deck_id
WHERE player.id = :'account_id'
ON CONFLICT (user_id, magic_id) DO NOTHING;

COMMIT;
