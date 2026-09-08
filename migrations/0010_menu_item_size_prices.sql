begin;

-- Empty overrides preserve the existing single-price catalog and order snapshots.
create function valid_menu_size_prices(prices jsonb, sizes text[], base_price numeric)
returns boolean language sql immutable as $$
    select case when jsonb_typeof(prices) <> 'object' then false else
        not exists (
            select 1 from jsonb_each_text(prices) as entry(size, price)
            where not (size = any(sizes))
               or size not in ('P', 'M', 'G')
               or price is null
               or price !~ '^[0-9]{1,8}(\.[0-9]{1,2})?$'
        ) and (
            prices = '{}'::jsonb or base_price is not null
            or prices ?& sizes
        )
    end;
$$;

alter table menu_items
    add column size_prices jsonb not null default '{}'::jsonb,
    add constraint menu_items_size_prices_valid
        check (valid_menu_size_prices(size_prices, size_options, price));

commit;
