/*
DROP TABLE IF EXISTS associacao_unidade_saude;

CREATE TABLE associacao_unidade_saude
(
    nome character varying(255) NOT NULL,
    codigo_cnes character varying(7)  NOT NULL,
    eh_regulado boolean,
    id_unidade_saude integer,
    CONSTRAINT associacao_unidade_saude_pkey PRIMARY KEY (codigo_cnes),
    CONSTRAINT associacao_unidade_saude_id_unidade_saude_fkey FOREIGN KEY (id_unidade_saude)
        REFERENCES public.unidade_saude (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE associacao_unidade_saude
    OWNER to postgres;

INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL REGIONAL ALFREDO MESQUITA FILHO/MATERNIDADE (MACAÍBA)', '2473577', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('UPA - BELO HORIZONTE (MOSSORÓ/RN)', '6902235', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL REGIONAL TELECILA FREITAS FONTES (CAICÓ/RN) SERIDÓ', '6778550', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('UPA - SANTO ANTÔNIO (MOSSORÓ/RN)', '5584523', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL REGIONAL LINDOLFO GOMES VIDAL - SANTO ANTÔNIO/RN', '2375265', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL REGIONAL MONSENHOR EXPEDITO (SÃO PAULO DO POTENGI/RN)', '2475227', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL REGIONAL DR. CLEODON CARLOS DE ANDRADE (PAU DOS FERROS/RN)', '2409275', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL DR. RODOLFO FERNANDES (HAPVIDA - MOSSORÓ/RN)', '5608910', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL REGIONAL DE APODI', '2410443', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL UNIVERSITÁRIO ONOFRE LOPES (HUOL)', '2653982', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL REGIONAL DE JOÃO CÂMARA', '2474751', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('CASA DE SAÚDE SÃO LUCAS - NATAL/RN', '2654016', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL UNIMED NATAL', '3649563', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL VARELA SANTIAGO', '2409151', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('UPA - CIDADE DA ESPERANÇA (NATAL/RN)', '7408765', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('UPA - MACAÍBA', '6742017', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('UPA - PAJUÇARA (NATAL/RN)', '6531288', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('POLICLÍNICA DO ALECRIM (LIGA)', '2798727', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL DR. ANTÔNIO PRUDENTE (HAPVIDA - NATAL/RN)', '2654024', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL MARIA ALICE FERNANDES (HMAF)', '2654261', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL WILSON ROSADO - MOSSORÓ', '2371707', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL DR. JOSÉ PEDRO BEZERRA (SANTA CATARINA)', '2408570', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('PROMATER HOSPITAL E MATERNIDADE', '2654032', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('UPA - POTENGI (NATAL/RN)', '7923287', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('UPA - PARNAMIRIM', '7885199', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL SÃO LUIZ (MOSSORÓ)', '9119701', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL MATERNIDADE BELARMINA MONTE (SÃO GONÇALO)', '4014235', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('UPA - CIDADE SATÉLITE (NATAL/RN)', '9361936', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL MONSENHOR WALFREDO GURGEL (HMWG)', '2653923', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL DR. RUY PEREIRA DOS SANTOS', '5314267', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL MUNICIPAL MANOEL LUCAS DE MIRANDA - GUAMARÉ', '2474506', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL DR. LUIZ ANTÔNIO (LIGA)', '2409194', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL REGIONAL DE SANTA CRUZ', '4014138', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL REGIONAL TARCÍSIO MAIA (HRTM)', '2503689', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL DO CORAÇÃO DE NATAL (HCN)', '8003629', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL GISELDA TRIGUEIRO', '4013484', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL DR. DEOCLÉCIO MARQUES DE LUCENA (HDML)', '3515168', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL CORONEL PEDRO GERMANO (HOSPITAL DA POLÍCIA)', '2679469', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('UPA - SÃO JOSÉ DE MIPIBU', '9383174', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL DOS PESCADORES', '0114626', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('MATERNIDADE ESCOLA JANUÁRIO CICCO (MEJC)', '2409208', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL MEMORIAL SÃO FRANCISCO', '2408252', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL RIO GRANDE', '2656930', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL MATERNIDADE ALMEIDA CASTRO (APAMIM - MOSSORÓ)', '2410281', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL MUNICIPAL DE NATAL (HMN)', '3708926', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL RAFAEL FERNANDES (HRF)', '2503654', false);
INSERT INTO associacao_unidade_saude (nome, codigo_cnes, eh_regulado) VALUES ('HOSPITAL UNIVERSITÁRIO ANA BEZERRA (HUAB)', '4014111', false);

*/
DROP VIEW IF EXISTS vw_leitos_dados_teste;

DROP VIEW IF EXISTS vw_leitos_dados;

DROP VIEW IF EXISTS vw_censo_leitos_internados;
CREATE VIEW vw_censo_leitos_internados AS
SELECT
	l.cod_referencia as leito_cod_referencia,
	p.nome as paciente_nome,
	p.data_nascimento as paciente_data_nascimento,
	m.codigo_municipio as paciente_municipio_codigo,
	m.nome as paciente_municipio_nome,
	i.diagnostico,
	i.codigo_do_exame as requisicao_gal,
	i.data_admissao as internacao_admissao,
	i.data_liberacao as internacao_liberacao,
	i.motivo_liberacao as internacao_motivo_liberacao,
	l.ativo as leito_ativo,
	l.motivo_bloqueio as leito_motivo_bloqueio,
	l.situacao_leito as leito_situacao_leito,
	l.tipo_leito as leito_tipo_leito,
	u.ativo as unidade_ativo,
	u.nome as unidade_nome,
	u.tipo_unidade_saude as unidade_tipo,
	mu.codigo_municipio as unidade_municipio_codigo,
	mu.nome as unidade_municipio_nome
from internacao i
inner join paciente_leito p on i.paciente_leito_id_paciente_leito = p.id_paciente_leito
inner join leito l on i.internacao_id = l.id_leito
inner join municipio m on p.id_municipio = m.id_municipio
inner join unidade_saude u on l.unidade_saude_id = u.id
inner join municipio mu on u.id_municipio = mu.id_municipio
where i.motivo_liberacao is null
;

DROP VIEW IF EXISTS vw_censo_leitos_obitos;
CREATE VIEW vw_censo_leitos_obitos AS
SELECT
	l.cod_referencia as leito_cod_referencia,
	p.nome as paciente_nome,
	p.data_nascimento as paciente_data_nascimento,
	m.codigo_municipio as paciente_municipio_codigo,
	m.nome as paciente_municipio_nome,
	i.diagnostico,
	i.codigo_do_exame as requisicao_gal,
	i.data_admissao as internacao_admissao,
	i.data_liberacao as internacao_liberacao,
	i.motivo_liberacao as internacao_motivo_liberacao,
	l.ativo as leito_ativo,
	l.motivo_bloqueio as leito_motivo_bloqueio,
	l.situacao_leito as leito_situacao_leito,
	l.tipo_leito as leito_tipo_leito,
	u.ativo as unidade_ativo,
	u.nome as unidade_nome,
	u.tipo_unidade_saude as unidade_tipo,
	mu.codigo_municipio as unidade_municipio_codigo,
	mu.nome as unidade_municipio_nome
from internacao i
inner join paciente_leito p on i.paciente_leito_id_paciente_leito = p.id_paciente_leito
inner join leito l on i.leito_id_leito = l.id_leito
inner join municipio m on p.id_municipio = m.id_municipio
inner join unidade_saude u on l.unidade_saude_id = u.id
inner join municipio mu on u.id_municipio = mu.id_municipio
WHERE i.motivo_liberacao = 'OBITO'
;

DROP VIEW IF EXISTS vw_censo_leitos_alta;

CREATE VIEW vw_censo_leitos_alta AS
SELECT
	l.cod_referencia as leito_cod_referencia,
	p.nome as paciente_nome,
	p.data_nascimento as paciente_data_nascimento,
	m.codigo_municipio as paciente_municipio_codigo,
	m.nome as paciente_municipio_nome,
	i.diagnostico,
	i.codigo_do_exame as requisicao_gal,
	i.data_admissao as internacao_admissao,
	i.data_liberacao as internacao_liberacao,
	i.motivo_liberacao as internacao_motivo_liberacao,
	l.ativo as leito_ativo,
	l.motivo_bloqueio as leito_motivo_bloqueio,
	l.situacao_leito as leito_situacao_leito,
	l.tipo_leito as leito_tipo_leito,
	u.ativo as unidade_ativo,
	u.nome as unidade_nome,
	u.tipo_unidade_saude as unidade_tipo,
	mu.codigo_municipio as unidade_municipio_codigo,
	mu.nome as unidade_municipio_nome
from internacao i
inner join paciente_leito p on i.paciente_leito_id_paciente_leito = p.id_paciente_leito
inner join leito l on i.leito_id_leito = l.id_leito
inner join municipio m on p.id_municipio = m.id_municipio
inner join unidade_saude u on l.unidade_saude_id = u.id
inner join municipio mu on u.id_municipio = mu.id_municipio
WHERE i.motivo_liberacao = 'ALTA'
;

CREATE VIEW vw_leitos_dados AS
select
    json_build_object(
        'internados', (select json_agg(internados) from vw_censo_leitos_internados as internados),
		'obitos', (select json_agg(internados) from vw_censo_leitos_obitos as internados),
		'altas', (select json_agg(internados) from vw_censo_leitos_alta as internados)
    ) as dados;


usar select dados from vw_leitos_dados

retorna os dados no formato:
{
    "internados": [
        {
            "leito_cod_referencia": "UCHLA ENFE - 03",
            "paciente_nome": "MARIA SENA DA SILVA",
            "paciente_data_nascimento": "1936-07-21",
            "paciente_municipio_codigo": 8102,
            "paciente_municipio_nome": "Natal",
            "diagnostico": "COVID-19 CONFIRMADO",
            "requisicao_gal": "",
            "internacao_admissao": "2020-05-27",
            "internacao_liberacao": null,
            "internacao_motivo_liberacao": null,
            "leito_ativo": true,
            "leito_motivo_bloqueio": null,
            "leito_situacao_leito": "OCUPADO",
            "leito_tipo_leito": "ENFERMARIA",
            "unidade_ativo": true,
            "unidade_nome": "HOSPITAL DR. LUIZ ANTÔNIO (LIGA)",
            "unidade_tipo": "FILANTROPICA"
        },
    ],
    "obitos": [
        {
            "leito_cod_referencia": "UTI",
            "paciente_nome": "MATHEUS ACIOLE DA COSTA",
            "paciente_data_nascimento": "1996-11-04",
            "paciente_municipio_codigo": 8102,
            "paciente_municipio_nome": "Natal",
            "diagnostico": "COVID-19 CONFIRMADO",
            "requisicao_gal": null,
            "internacao_admissao": "2020-04-08",
            "internacao_liberacao": "2020-04-09",
            "internacao_motivo_liberacao": "OBITO",
            "leito_ativo": false,
            "leito_motivo_bloqueio": null,
            "leito_situacao_leito": "LIVRE",
            "leito_tipo_leito": "INTENSIVA",
            "unidade_ativo": true,
            "unidade_nome": "HOSPITAL DR. ANTÔNIO PRUDENTE (HAPVIDA - NATAL/RN)",
            "unidade_tipo": "PRIVADA"
        },
    ]
}
*/
