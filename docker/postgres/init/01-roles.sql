-- Ilova roli: jadval egasi EMAS va BYPASSRLS yo‘q, shuning uchun RLS siyosatlari majburiy ishlaydi.
-- Parol faqat lokal ishlab chiqish uchun; production’da secret manager’dan beriladi.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'uniload_app') THEN
    CREATE ROLE uniload_app LOGIN PASSWORD 'uniload_app' NOSUPERUSER NOBYPASSRLS;
  END IF;
END $$;

GRANT CONNECT ON DATABASE uniload TO uniload_app;
CREATE DATABASE uniload_test OWNER uniload;
GRANT CONNECT ON DATABASE uniload_test TO uniload_app;
