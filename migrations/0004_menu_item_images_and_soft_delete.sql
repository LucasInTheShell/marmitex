-- Dish image metadata and recoverable catalog deletion.

begin;

alter table menu_items
  add column image_key text,
  add column deleted_at timestamptz,
  add constraint menu_items_image_key_not_blank
    check (image_key is null or btrim(image_key) <> '');

create index menu_items_active_name_idx
  on menu_items (name)
  where deleted_at is null;

commit;
