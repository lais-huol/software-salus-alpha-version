DROP VIEW vw_solicitacacoes_leito;

CREATE VIEW vw_solicitacacoes_leito AS
SELECT
    s.id as solicitacao_id,
    liberacao.liberacao_data,
	liberacao.liberacao_motivo,
	liberacao.liberacao_tipo_leito,
	pf.nome,
	to_char(pf.data_nascimento::timestamp with time zone, 'DD/MM/YYYY'::text) AS data_nascimento,
	date_part('year'::text, age(pf.data_nascimento::timestamp with time zone)) AS idade,
	pa.cartao_sus,
	s.data_cadastro,
	s.cancelada_em,
	s.numero_gal,
	s.tipo_caso,
	s.situacao,
	es.cnes AS estabelecimento_solicitante_cnes,
	es.nome AS estabelecimento_solicitante_nome,
	esm.nome as estabelecimento_solicitante_municipio_nome,
	esm.codigo as estabelecimento_solicitante_municipio_codigo_ibge,
	ep.cnes AS estabelecimento_prestador_cnes,
	ep.nome AS estabelecimento_prestador_nome,
	epm.nome as estabelecimento_prestador_municipio_nome,
	epm.codigo as estabelecimento_prestador_municipio_codigo_ibge
   FROM base_solicitacao s
	 JOIN base_estabelecimento es ON s.estabelecimento_solicitante_id = es.id
	 INNER JOIN base_municipio esm on es.municipio_id = esm.id
	 LEFT JOIN base_estabelecimento ep ON s.estabelecimento_prestador_id = ep.id
	 LEFT JOIN base_municipio epm on ep.municipio_id = epm.id
	 JOIN base_paciente pa ON s.paciente_id = pa.id
	 JOIN base_pessoafisica pf ON pa.pessoa_fisica_id = pf.id
	 LEFT JOIN ( SELECT base_paciente.id AS paciente_id,
			to_char(max(data_saida), 'DD/MM/YYYY') as liberacao_data,
				CASE
					WHEN base_historicoocupacaoleito.motivo_liberacao::text = '1' THEN 'Alta'
					WHEN base_historicoocupacaoleito.motivo_liberacao::text = '2' THEN 'Óbito'
					ELSE NULL::text
				END AS liberacao_motivo,
			base_tipoleito.descricao AS liberacao_tipo_leito
		   FROM base_historicoocupacaoleito
			 INNER JOIN base_leito ON base_historicoocupacaoleito.leito_id = base_leito.id
			 INNER JOIN base_tipoleito ON base_leito.tipo_id = base_tipoleito.id
			 JOIN base_solicitacao ON base_historicoocupacaoleito.solicitacao_id = base_solicitacao.id
			 JOIN base_paciente ON base_solicitacao.paciente_id = base_paciente.id
		  WHERE base_historicoocupacaoleito.motivo_liberacao IS NOT NULL AND base_historicoocupacaoleito.motivo_liberacao::text <> '3'::text
		  GROUP BY base_paciente.id, base_historicoocupacaoleito.motivo_liberacao, base_tipoleito.descricao) liberacao ON liberacao.paciente_id = pa.id
  WHERE s.situacao <> 'Cancelada';