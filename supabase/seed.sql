-- Local development seed. Creates the Mavi staff credentials so there is a way
-- into the admin area on a fresh database. Companies are created from the
-- admin UI, not seeded.

insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password,
  email_confirmed_at, created_at, updated_at,
  raw_app_meta_data, raw_user_meta_data
) values (
  '00000000-0000-0000-0000-000000000000',
  '11111111-1111-1111-1111-111111111111',
  'authenticated', 'authenticated',
  'admin@mavi.local',
  crypt('mavi-admin-2026', gen_salt('bf')),
  now(), now(), now(),
  '{"provider":"email","providers":["email"]}', '{}'
);

insert into auth.identities (
  provider_id, user_id, identity_data, provider, last_sign_in_at,
  created_at, updated_at
) values (
  '11111111-1111-1111-1111-111111111111',
  '11111111-1111-1111-1111-111111111111',
  '{"sub":"11111111-1111-1111-1111-111111111111","email":"admin@mavi.local","email_verified":true,"phone_verified":false}',
  'email', now(), now(), now()
);

insert into accounts (id, name, email, company_id, role) values (
  '11111111-1111-1111-1111-111111111111',
  'Administração Mavi',
  'admin@mavi.local',
  null,
  'admin'
);
