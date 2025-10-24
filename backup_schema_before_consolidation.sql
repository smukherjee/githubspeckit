--
-- PostgreSQL database dump
--

\restrict KUQchsPfE8h1mNQtymcdf8TkjKtet4ty5rYpCIdR8honm46yFHaOr8Rcn4fTSXm

-- Dumped from database version 14.19 (Homebrew)
-- Dumped by pg_dump version 14.19 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: decision; Type: TYPE; Schema: public; Owner: infysight_dbadmin
--

CREATE TYPE public.decision AS ENUM (
    'ALLOW',
    'DENY',
    'ABSTAIN'
);


ALTER TYPE public.decision OWNER TO infysight_dbadmin;

--
-- Name: flag_state; Type: TYPE; Schema: public; Owner: infysight_dbadmin
--

CREATE TYPE public.flag_state AS ENUM (
    'enabled',
    'disabled'
);


ALTER TYPE public.flag_state OWNER TO infysight_dbadmin;

--
-- Name: mfa_factor_type; Type: TYPE; Schema: public; Owner: infysight_dbadmin
--

CREATE TYPE public.mfa_factor_type AS ENUM (
    'totp',
    'webauthn'
);


ALTER TYPE public.mfa_factor_type OWNER TO infysight_dbadmin;

--
-- Name: tenant_status; Type: TYPE; Schema: public; Owner: infysight_dbadmin
--

CREATE TYPE public.tenant_status AS ENUM (
    'active',
    'soft_deleted',
    'disabled'
);


ALTER TYPE public.tenant_status OWNER TO infysight_dbadmin;

--
-- Name: user_status; Type: TYPE; Schema: public; Owner: infysight_dbadmin
--

CREATE TYPE public.user_status AS ENUM (
    'invited',
    'active',
    'disabled'
);


ALTER TYPE public.user_status OWNER TO infysight_dbadmin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO infysight_dbadmin;

--
-- Name: audit_events; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.audit_events (
    event_id uuid NOT NULL,
    tenant_id uuid,
    actor_user_id uuid,
    action_type character varying(100) NOT NULL,
    target_ref character varying(255) NOT NULL,
    metadata json DEFAULT '{}'::json NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.audit_events OWNER TO infysight_dbadmin;

--
-- Name: feature_flags; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.feature_flags (
    flag_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    key character varying(100) NOT NULL,
    state public.flag_state DEFAULT 'disabled'::public.flag_state NOT NULL,
    variant character varying(50),
    rules json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL
);


ALTER TABLE public.feature_flags OWNER TO infysight_dbadmin;

--
-- Name: invitations; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.invitations (
    invitation_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    email character varying(255) NOT NULL,
    token_hash character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    accepted_at timestamp with time zone
);


ALTER TABLE public.invitations OWNER TO infysight_dbadmin;

--
-- Name: key_rotation_records; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.key_rotation_records (
    key_version integer NOT NULL,
    activated_at timestamp with time zone NOT NULL,
    retired_at timestamp with time zone,
    algorithm character varying(50) NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


ALTER TABLE public.key_rotation_records OWNER TO infysight_dbadmin;

--
-- Name: key_rotation_records_key_version_seq; Type: SEQUENCE; Schema: public; Owner: infysight_dbadmin
--

CREATE SEQUENCE public.key_rotation_records_key_version_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.key_rotation_records_key_version_seq OWNER TO infysight_dbadmin;

--
-- Name: key_rotation_records_key_version_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: infysight_dbadmin
--

ALTER SEQUENCE public.key_rotation_records_key_version_seq OWNED BY public.key_rotation_records.key_version;


--
-- Name: password_reset_requests; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.password_reset_requests (
    reset_id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(64) NOT NULL,
    issued_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    consumed_at timestamp with time zone
);


ALTER TABLE public.password_reset_requests OWNER TO infysight_dbadmin;

--
-- Name: policies; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.policies (
    policy_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    rules json DEFAULT '[]'::json NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL
);


ALTER TABLE public.policies OWNER TO infysight_dbadmin;

--
-- Name: policy_evaluation_logs; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.policy_evaluation_logs (
    eval_id uuid NOT NULL,
    policy_id uuid NOT NULL,
    decision public.decision NOT NULL,
    latency_ms integer NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    correlation_id character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.policy_evaluation_logs OWNER TO infysight_dbadmin;

--
-- Name: schema_version; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.schema_version (
    version character varying(20) NOT NULL,
    applied_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    description text,
    checksum character varying(64)
);


ALTER TABLE public.schema_version OWNER TO infysight_dbadmin;

--
-- Name: tenants; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.tenants (
    tenant_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    status public.tenant_status DEFAULT 'active'::public.tenant_status NOT NULL,
    config_version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid
);


ALTER TABLE public.tenants OWNER TO infysight_dbadmin;

--
-- Name: token_replay_records; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.token_replay_records (
    jti character varying(255) NOT NULL,
    expires_at double precision NOT NULL,
    registered_at double precision NOT NULL,
    tenant_id uuid
);


ALTER TABLE public.token_replay_records OWNER TO infysight_dbadmin;

--
-- Name: user_details; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.user_details (
    user_id uuid NOT NULL,
    full_name character varying(100),
    phone character varying(20),
    address text,
    photo_display_url character varying(512),
    photo_thumbnail_url character varying(512),
    photo_avatar_url character varying(512),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by uuid NOT NULL,
    updated_by uuid NOT NULL
);


ALTER TABLE public.user_details OWNER TO infysight_dbadmin;

--
-- Name: TABLE user_details; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON TABLE public.user_details IS 'User profile details (one-to-one with users)';


--
-- Name: COLUMN user_details.user_id; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.user_id IS 'FK to users.user_id';


--
-- Name: COLUMN user_details.full_name; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.full_name IS 'User full name';


--
-- Name: COLUMN user_details.phone; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.phone IS 'Phone number (E.164 format recommended)';


--
-- Name: COLUMN user_details.address; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.address IS 'Postal address';


--
-- Name: COLUMN user_details.photo_display_url; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.photo_display_url IS 'Display photo URL (640x640)';


--
-- Name: COLUMN user_details.photo_thumbnail_url; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.photo_thumbnail_url IS 'Thumbnail photo URL (96x96)';


--
-- Name: COLUMN user_details.photo_avatar_url; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.photo_avatar_url IS 'Avatar photo URL (48x48)';


--
-- Name: COLUMN user_details.created_at; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.created_at IS 'Record creation timestamp';


--
-- Name: COLUMN user_details.updated_at; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.updated_at IS 'Record last update timestamp';


--
-- Name: COLUMN user_details.created_by; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.created_by IS 'User who created the record';


--
-- Name: COLUMN user_details.updated_by; Type: COMMENT; Schema: public; Owner: infysight_dbadmin
--

COMMENT ON COLUMN public.user_details.updated_by IS 'User who last updated the record';


--
-- Name: user_mfa; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.user_mfa (
    user_id uuid NOT NULL,
    factor_type public.mfa_factor_type NOT NULL,
    enrolled_at timestamp with time zone NOT NULL,
    last_used_at timestamp with time zone,
    secret_hash character varying(255),
    credential_public_key bytea,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid
);


ALTER TABLE public.user_mfa OWNER TO infysight_dbadmin;

--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.user_roles (
    user_id uuid NOT NULL,
    role_id character varying(50) NOT NULL
);


ALTER TABLE public.user_roles OWNER TO infysight_dbadmin;

--
-- Name: users; Type: TABLE; Schema: public; Owner: infysight_dbadmin
--

CREATE TABLE public.users (
    user_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    email character varying(255) NOT NULL,
    status public.user_status DEFAULT 'invited'::public.user_status NOT NULL,
    password_hash character varying(255),
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by uuid,
    updated_by uuid
);


ALTER TABLE public.users OWNER TO infysight_dbadmin;

--
-- Name: key_rotation_records key_version; Type: DEFAULT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.key_rotation_records ALTER COLUMN key_version SET DEFAULT nextval('public.key_rotation_records_key_version_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_events audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_pkey PRIMARY KEY (event_id);


--
-- Name: feature_flags feature_flags_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.feature_flags
    ADD CONSTRAINT feature_flags_pkey PRIMARY KEY (flag_id);


--
-- Name: invitations invitations_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_pkey PRIMARY KEY (invitation_id);


--
-- Name: key_rotation_records key_rotation_records_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.key_rotation_records
    ADD CONSTRAINT key_rotation_records_pkey PRIMARY KEY (key_version);


--
-- Name: password_reset_requests password_reset_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.password_reset_requests
    ADD CONSTRAINT password_reset_requests_pkey PRIMARY KEY (reset_id);


--
-- Name: password_reset_requests password_reset_requests_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.password_reset_requests
    ADD CONSTRAINT password_reset_requests_token_hash_key UNIQUE (token_hash);


--
-- Name: user_details pk_user_details; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.user_details
    ADD CONSTRAINT pk_user_details PRIMARY KEY (user_id);


--
-- Name: policies policies_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.policies
    ADD CONSTRAINT policies_pkey PRIMARY KEY (policy_id);


--
-- Name: policy_evaluation_logs policy_evaluation_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.policy_evaluation_logs
    ADD CONSTRAINT policy_evaluation_logs_pkey PRIMARY KEY (eval_id);


--
-- Name: schema_version schema_version_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.schema_version
    ADD CONSTRAINT schema_version_pkey PRIMARY KEY (version);


--
-- Name: tenants tenants_name_key; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_name_key UNIQUE (name);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (tenant_id);


--
-- Name: token_replay_records token_replay_records_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.token_replay_records
    ADD CONSTRAINT token_replay_records_pkey PRIMARY KEY (jti);


--
-- Name: user_mfa user_mfa_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.user_mfa
    ADD CONSTRAINT user_mfa_pkey PRIMARY KEY (user_id, factor_type);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (user_id, role_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: idx_users_email_tenant; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE UNIQUE INDEX idx_users_email_tenant ON public.users USING btree (email, tenant_id);


--
-- Name: ix_audit_events_action_created; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_audit_events_action_created ON public.audit_events USING btree (action_type, created_at);


--
-- Name: ix_audit_events_tenant_created; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_audit_events_tenant_created ON public.audit_events USING btree (tenant_id, created_at);


--
-- Name: ix_feature_flags_state; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_feature_flags_state ON public.feature_flags USING btree (state);


--
-- Name: ix_feature_flags_status; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_feature_flags_status ON public.feature_flags USING btree (status);


--
-- Name: ix_feature_flags_tenant_key; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE UNIQUE INDEX ix_feature_flags_tenant_key ON public.feature_flags USING btree (tenant_id, key);


--
-- Name: ix_invitations_expires_at; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_invitations_expires_at ON public.invitations USING btree (expires_at);


--
-- Name: ix_invitations_tenant_email; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_invitations_tenant_email ON public.invitations USING btree (tenant_id, email);


--
-- Name: ix_password_resets_token_hash; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_password_resets_token_hash ON public.password_reset_requests USING btree (token_hash);


--
-- Name: ix_password_resets_user_expires; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_password_resets_user_expires ON public.password_reset_requests USING btree (user_id, expires_at);


--
-- Name: ix_policies_created_at; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_policies_created_at ON public.policies USING btree (created_at);


--
-- Name: ix_policies_status; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_policies_status ON public.policies USING btree (status);


--
-- Name: ix_policies_tenant_id; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_policies_tenant_id ON public.policies USING btree (tenant_id);


--
-- Name: ix_policy_eval_logs_decision_created; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_policy_eval_logs_decision_created ON public.policy_evaluation_logs USING btree (decision, created_at);


--
-- Name: ix_policy_eval_logs_policy_created; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_policy_eval_logs_policy_created ON public.policy_evaluation_logs USING btree (policy_id, created_at);


--
-- Name: ix_policy_eval_logs_tenant_created; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_policy_eval_logs_tenant_created ON public.policy_evaluation_logs USING btree (tenant_id, created_at);


--
-- Name: ix_tenants_name; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_tenants_name ON public.tenants USING btree (name);


--
-- Name: ix_tenants_status_created_at; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_tenants_status_created_at ON public.tenants USING btree (status, created_at);


--
-- Name: ix_token_replay_expires_at; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_token_replay_expires_at ON public.token_replay_records USING btree (expires_at);


--
-- Name: ix_token_replay_tenant_id; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_token_replay_tenant_id ON public.token_replay_records USING btree (tenant_id);


--
-- Name: ix_user_details_created_at; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_user_details_created_at ON public.user_details USING btree (created_at);


--
-- Name: ix_user_details_updated_at; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_user_details_updated_at ON public.user_details USING btree (updated_at);


--
-- Name: ix_users_tenant_email; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE UNIQUE INDEX ix_users_tenant_email ON public.users USING btree (tenant_id, email);


--
-- Name: ix_users_tenant_status; Type: INDEX; Schema: public; Owner: infysight_dbadmin
--

CREATE INDEX ix_users_tenant_status ON public.users USING btree (tenant_id, status);


--
-- Name: feature_flags feature_flags_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.feature_flags
    ADD CONSTRAINT feature_flags_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(tenant_id) ON DELETE CASCADE;


--
-- Name: user_details fk_user_details_created_by; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.user_details
    ADD CONSTRAINT fk_user_details_created_by FOREIGN KEY (created_by) REFERENCES public.users(user_id);


--
-- Name: user_details fk_user_details_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.user_details
    ADD CONSTRAINT fk_user_details_updated_by FOREIGN KEY (updated_by) REFERENCES public.users(user_id);


--
-- Name: user_details fk_user_details_user_id; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.user_details
    ADD CONSTRAINT fk_user_details_user_id FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: invitations invitations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.invitations
    ADD CONSTRAINT invitations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(tenant_id) ON DELETE CASCADE;


--
-- Name: password_reset_requests password_reset_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.password_reset_requests
    ADD CONSTRAINT password_reset_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: policies policies_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.policies
    ADD CONSTRAINT policies_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(tenant_id) ON DELETE CASCADE;


--
-- Name: policy_evaluation_logs policy_evaluation_logs_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.policy_evaluation_logs
    ADD CONSTRAINT policy_evaluation_logs_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.policies(policy_id) ON DELETE CASCADE;


--
-- Name: user_mfa user_mfa_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.user_mfa
    ADD CONSTRAINT user_mfa_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: users users_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: infysight_dbadmin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(tenant_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict KUQchsPfE8h1mNQtymcdf8TkjKtet4ty5rYpCIdR8honm46yFHaOr8Rcn4fTSXm

