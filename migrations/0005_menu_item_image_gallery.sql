-- Normalize dish images into an ordered gallery with one optional primary image.

begin;

create table menu_item_images (
  id uuid primary key default gen_random_uuid(),
  menu_item_id uuid not null references menu_items (id) on delete cascade,
  object_key text not null unique,
  sort_order integer not null check (sort_order >= 0),
  is_primary boolean not null default false,
  created_at timestamptz not null default now(),
  constraint menu_item_images_object_key_not_blank check (btrim(object_key) <> ''),
  constraint menu_item_images_item_order_unique unique (menu_item_id, sort_order)
);

create unique index menu_item_images_one_primary_idx
  on menu_item_images (menu_item_id)
  where is_primary;

create index menu_item_images_item_idx
  on menu_item_images (menu_item_id, sort_order);

insert into menu_item_images (menu_item_id, object_key, sort_order, is_primary)
select id, image_key, 0, true
from menu_items
where image_key is not null;

alter table menu_items
  drop constraint menu_items_image_key_not_blank,
  drop column image_key;

commit;
