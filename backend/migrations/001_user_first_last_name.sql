DO $$
BEGIN

    -- Jei egzistuoja full_name ir neegzistuoja first_name
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name='users'
        AND column_name='full_name'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name='users'
        AND column_name='first_name'
    )
    THEN
        ALTER TABLE users
        RENAME COLUMN full_name TO first_name;
    END IF;

    -- Jei nėra first_name
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name='users'
        AND column_name='first_name'
    )
    THEN
        ALTER TABLE users
        ADD COLUMN first_name VARCHAR(255);
    END IF;

    -- Jei nėra last_name
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name='users'
        AND column_name='last_name'
    )
    THEN
        ALTER TABLE users
        ADD COLUMN last_name VARCHAR(255);
    END IF;

END $$;