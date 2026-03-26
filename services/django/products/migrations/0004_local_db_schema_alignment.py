from django.db import migrations, models


DOMAIN_TABLES_SQL = """
CREATE SEQUENCE IF NOT EXISTS public.breed_meta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.breed_meta (
    id integer NOT NULL,
    species character varying(10),
    breed_name character varying(100),
    breed_name_en character varying(100),
    group_name character varying(50),
    size_class text[],
    age_group character varying(20),
    care_difficulty integer,
    preferred_food text,
    health_products text,
    chunk_text text,
    embedding public.vector(1024),
    search_vector tsvector
);

ALTER SEQUENCE public.breed_meta_id_seq OWNED BY public.breed_meta.id;
ALTER TABLE ONLY public.breed_meta
    ALTER COLUMN id SET DEFAULT nextval('public.breed_meta_id_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'breed_meta_pkey'
          AND conrelid = 'public.breed_meta'::regclass
    ) THEN
        ALTER TABLE ONLY public.breed_meta
            ADD CONSTRAINT breed_meta_pkey PRIMARY KEY (id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_breed_meta_breed_age
    ON public.breed_meta USING btree (breed_name, age_group);
CREATE INDEX IF NOT EXISTS idx_breed_meta_embedding
    ON public.breed_meta USING hnsw (embedding public.vector_cosine_ops)
    WITH (m = '16', ef_construction = '64');
CREATE INDEX IF NOT EXISTS idx_breed_meta_search_vector
    ON public.breed_meta USING gin (search_vector);
CREATE INDEX IF NOT EXISTS idx_breed_meta_species
    ON public.breed_meta USING btree (species);

CREATE SEQUENCE IF NOT EXISTS public.domain_qna_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.domain_qna (
    id integer NOT NULL,
    no integer NOT NULL,
    species character varying(10),
    category character varying(50),
    source character varying(20),
    chunk_text text,
    embedding public.vector(1024),
    search_vector tsvector
);

ALTER SEQUENCE public.domain_qna_id_seq OWNED BY public.domain_qna.id;
ALTER TABLE ONLY public.domain_qna
    ALTER COLUMN id SET DEFAULT nextval('public.domain_qna_id_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'domain_qna_pkey'
          AND conrelid = 'public.domain_qna'::regclass
    ) THEN
        ALTER TABLE ONLY public.domain_qna
            ADD CONSTRAINT domain_qna_pkey PRIMARY KEY (id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_domain_qna_embedding
    ON public.domain_qna USING hnsw (embedding public.vector_cosine_ops)
    WITH (m = '16', ef_construction = '64');
CREATE INDEX IF NOT EXISTS idx_domain_qna_search_vector
    ON public.domain_qna USING gin (search_vector);
CREATE INDEX IF NOT EXISTS idx_domain_qna_species
    ON public.domain_qna USING btree (species);

ALTER TABLE public.product ALTER COLUMN "냄새" DROP NOT NULL;
ALTER TABLE public.product ALTER COLUMN "기호성" DROP NOT NULL;
ALTER TABLE public.product ALTER COLUMN "생체반응" DROP NOT NULL;
ALTER TABLE public.product ALTER COLUMN "가격/구매" DROP NOT NULL;
ALTER TABLE public.product ALTER COLUMN "배송/포장" DROP NOT NULL;
ALTER TABLE public.product ALTER COLUMN "성분/원료" DROP NOT NULL;
ALTER TABLE public.product ALTER COLUMN "소화/배변" DROP NOT NULL;
ALTER TABLE public.product ALTER COLUMN "제품 성상" DROP NOT NULL;
ALTER TABLE public.product ALTER COLUMN "냄새" SET DEFAULT 0;
ALTER TABLE public.product ALTER COLUMN "기호성" SET DEFAULT 0;
ALTER TABLE public.product ALTER COLUMN "생체반응" SET DEFAULT 0;
ALTER TABLE public.product ALTER COLUMN "가격/구매" SET DEFAULT 0;
ALTER TABLE public.product ALTER COLUMN "배송/포장" SET DEFAULT 0;
ALTER TABLE public.product ALTER COLUMN "성분/원료" SET DEFAULT 0;
ALTER TABLE public.product ALTER COLUMN "소화/배변" SET DEFAULT 0;
ALTER TABLE public.product ALTER COLUMN "제품 성상" SET DEFAULT 0;

ALTER TABLE public.review ALTER COLUMN "냄새" DROP NOT NULL;
ALTER TABLE public.review ALTER COLUMN "기호성" DROP NOT NULL;
ALTER TABLE public.review ALTER COLUMN "생체반응" DROP NOT NULL;
ALTER TABLE public.review ALTER COLUMN "가격/구매" DROP NOT NULL;
ALTER TABLE public.review ALTER COLUMN "배송/포장" DROP NOT NULL;
ALTER TABLE public.review ALTER COLUMN "성분/원료" DROP NOT NULL;
ALTER TABLE public.review ALTER COLUMN "소화/배변" DROP NOT NULL;
ALTER TABLE public.review ALTER COLUMN "제품 성상" DROP NOT NULL;
ALTER TABLE public.review ALTER COLUMN "냄새" SET DEFAULT 0;
ALTER TABLE public.review ALTER COLUMN "기호성" SET DEFAULT 0;
ALTER TABLE public.review ALTER COLUMN "생체반응" SET DEFAULT 0;
ALTER TABLE public.review ALTER COLUMN "가격/구매" SET DEFAULT 0;
ALTER TABLE public.review ALTER COLUMN "배송/포장" SET DEFAULT 0;
ALTER TABLE public.review ALTER COLUMN "성분/원료" SET DEFAULT 0;
ALTER TABLE public.review ALTER COLUMN "소화/배변" SET DEFAULT 0;
ALTER TABLE public.review ALTER COLUMN "제품 성상" SET DEFAULT 0;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0003_product_aspect_biological_response_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="aspect_biological_response",
            field=models.DecimalField(blank=True, db_column="생체반응", decimal_places=4, default=0.0, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="aspect_delivery_packaging",
            field=models.DecimalField(blank=True, db_column="배송/포장", decimal_places=4, default=0.0, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="aspect_digestion_stool",
            field=models.DecimalField(blank=True, db_column="소화/배변", decimal_places=4, default=0.0, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="aspect_ingredients_origin",
            field=models.DecimalField(blank=True, db_column="성분/원료", decimal_places=4, default=0.0, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="aspect_palatability",
            field=models.DecimalField(blank=True, db_column="기호성", decimal_places=4, default=0.0, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="aspect_price_purchase",
            field=models.DecimalField(blank=True, db_column="가격/구매", decimal_places=4, default=0.0, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="aspect_product_appearance",
            field=models.DecimalField(blank=True, db_column="제품 성상", decimal_places=4, default=0.0, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="aspect_smell",
            field=models.DecimalField(blank=True, db_column="냄새", decimal_places=4, default=0.0, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="aspect_biological_response",
            field=models.IntegerField(blank=True, db_column="생체반응", default=0, null=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="aspect_delivery_packaging",
            field=models.IntegerField(blank=True, db_column="배송/포장", default=0, null=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="aspect_digestion_stool",
            field=models.IntegerField(blank=True, db_column="소화/배변", default=0, null=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="aspect_ingredients_origin",
            field=models.IntegerField(blank=True, db_column="성분/원료", default=0, null=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="aspect_palatability",
            field=models.IntegerField(blank=True, db_column="기호성", default=0, null=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="aspect_price_purchase",
            field=models.IntegerField(blank=True, db_column="가격/구매", default=0, null=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="aspect_product_appearance",
            field=models.IntegerField(blank=True, db_column="제품 성상", default=0, null=True),
        ),
        migrations.AlterField(
            model_name="review",
            name="aspect_smell",
            field=models.IntegerField(blank=True, db_column="냄새", default=0, null=True),
        ),
        migrations.RunSQL(DOMAIN_TABLES_SQL, migrations.RunSQL.noop),
    ]
