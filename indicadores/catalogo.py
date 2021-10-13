from indicadores.enums import TipoVisualizacao, ValorFormaExbicao, TipoMapa
import collections

def get_catalogo_indicadores(chave=None):
    '''
        'pk_grafico': {
            'grafico': {
                'titulo': 'Número de casos suspeitos com Covid-19 por data, em Natal'
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'yAxis_title_text': 'Número de casos',
                'funcao': 'self._get_visualizacao,
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos_semana,
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': None,
                    },
                    'exclude': {
                        'dados__cbo': None,
                    },
                    'series_name': (
                            ('Data da Notificacao', 'data__month'),
                            ('Resultado do teste', 'dados__resultado_do_teste'),
                    ),
                    'dados_mapeamento': {'dados__resultado_do_teste': {
                                            'Negativo': 'Descartado',
                                            'Positivo': 'Confirmado',
                                            None: 'Suspeito'}
                    },
                    'fields_annotate' = {
                            'conteudo': Count('numero'),
                    },
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                    'dias_a_considerar': 7,
                    'semana_a_considerar': (0, 0),
                    'field_date': 'data',
                }
            }
        },
    :param self:
    :param chave:
    :return:
    '''
    dic_catalogo = {
        'data_ultima_atualizacao_esusve': {
            'titulo': 'Data da  Última Atualização com ESUSVE',
            'fonte': {
                'funcao': 'self.data_ultima_atualizacao_esusve',
            }
        },
        'data_do_boletim': {
            'titulo': 'Data do boletim',
            'fonte': {
                'funcao': 'self.data_do_boletim',
            }
        },
        'numero_do_boletim': {
            'titulo': 'Número do boletim',
            'fonte': {
                'funcao': 'self.numero_do_boletim',
            }
        },
        'numero_do_boletim_anterior_0': {
            'titulo': 'Número do boletim da semana atual',
            'fonte': {
                'funcao': 'self.numero_do_boletim',
                'parametros': {'semana_a_considerar': (0, 0)}
            }
        },
        'numero_do_boletim_anterior_1': {
            'titulo': 'Número do boletim da 1a semana anterior',
            'fonte': {
                'funcao': 'self.numero_do_boletim',
                'parametros': {'semana_a_considerar': (-1, -1)}
            }
        },
        'numero_do_boletim_anterior_2': {
            'titulo': 'Número do boletim da 2a semana anterior',
            'fonte': {
                'funcao': 'self.numero_do_boletim',
                'parametros': {'semana_a_considerar': (-2, -2)}
            }
        },
        'numero_do_boletim_anterior_3': {
            'titulo': 'Número do boletim da 3a semana anterior',
            'fonte': {
                'funcao': 'self.numero_do_boletim',
                'parametros': {'semana_a_considerar': (-3, -3)}
            }
        },
        'numero_do_boletim_anterior_4': {
            'titulo': 'Número do boletim da 4a semana anterior',
            'fonte': {
                'funcao': 'self.numero_do_boletim',
                'parametros': {'semana_a_considerar': (-4, -4)}
            }
        },
        'numero_do_boletim_anterior_5': {
            'titulo': 'Número do boletim da 5a semana anterior',
            'fonte': {
                'funcao': 'self.numero_do_boletim',
                'parametros': {'semana_a_considerar': (-5, -5)}
            }
        },
        'numero_do_boletim_anterior_6': {
            'titulo': 'Número do boletim da 6a semana anterior',
            'fonte': {
                'funcao': 'self.numero_do_boletim',
                'parametros': {'semana_a_considerar': (-6, -6)}
            }
        },
        'total_obitos_confirmados': {
            'titulo': 'Número de óbitos confirmados',
            'fonte': {
                'funcao': 'indicadores.get_obitos',
                'parametros': {
                    'filter': {
                        'confirmado_covid19': True,
                    },
                }
            }
        },
        'obitos_novos_confirmados_ultimo_7_dias': {
            'titulo': 'Número de óbitos confirmados nos últimos 7 dias',
            'fonte': {
                'funcao': 'indicadores.get_obitos',
                'parametros': {
                    'filter': {
                        'confirmado_covid19': True,
                    },
                    'dias_a_considerar': 7,
                }
            }
        },
        'mapa_de_obitos_por_bairro_endereco_moradia': {
            'titulo': 'Mapa dos óbitos para COVID-19 por bairro de endereço de moradia',
            'mapa': {
                'descricao': '',
                'geojson': 'indicadores/static/js/Natal_Bairros2.geo.json',
                'tipo': TipoMapa.PADRAO,
                'valor': 'Óbitos confirmados',
                'colunas': ['Bairro', 'Óbitos confirmados'],
                'mapeamento_colunas': ['code', 'value'],
                # 'mapeamento_valores': {'Bairro': {'SANTOS REIS': 'Santos Reis', 'ALECRIM': 'Alecrim'}},
                'dados_extra': {'categories': 'Bairro'}
            },
            'fonte': {
                'funcao': 'indicadores.get_obitos',
                'parametros': {
                    'filter': {
                        'confirmado_covid19': True,
                    },
                    'series_name': (
                    ('Bairro', 'bairro__nome'), ('Resultado dos testes', 'resultado_do_teste_covid_19'),),
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                    'dados_mapeamento': {
                        'resultado_do_teste_covid_19': {'Confirmado': 'Óbitos confirmados'},
                    },
                    'order_by': ['bairro__nome'],
                }
            }
        },
        'mapa_de_casos_confirmados_acumulados_por_bairro_endereco_moradia': {
            'titulo': 'Mapa dos casos confirmados acumulados para COVID-19 por bairro de endereço de moradia',
            'mapa': {
                'descricao': '',
                'geojson': 'indicadores/static/js/Natal_Bairros2.geo.json',
                'tipo': TipoMapa.PADRAO,
                'valor': 'Casos confirmados',
                'colunas': ['Bairro', 'Casos confirmados'],
                'mapeamento_colunas': ['code', 'value'],
                'mapeamento_valores': {'Bairro': {'SANTOS REIS': 'Santos Reis', 'ALECRIM': 'Alecrim'}},
                'dados_extra': {'categories': 'Bairro'}
            },
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Bairro', 'bairro__nome'),
                    ('Resultado dos testes', 'dados__resultado_do_teste'),),
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                    'dados_mapeamento': {'dados__resultado_do_teste': {'Negativo': 'Descartado', 'Positivo': 'Casos confirmados', None: 'Suspeito'}},
                    'order_by': ['bairro__nome'],
                }
            }
        },
        'mapa_de_calor_casos_confirmados_quinzenal': {
            'titulo': 'Mapa de calor dos casos confirmados para COVID-19 das duas últimas semanas',
            'mapa': {
                'descricao': '',
                'tipo': TipoMapa.CALOR,
            },
            'fonte': {
                'funcao': 'indicadores.get_dados_mapa_calor',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    # semana_a_considerar indica o periodo de semana a ser considerada no filtro para obtenção dos dados
                    # Se (-1, 0) irá gerar dados da semana anterior a semana especificada no boletim + a semana especificada
                    # Exemplo: se o boletim é referente a semana 26 (21.06 - 27.06), o parâmetro (0, 1) irá
                    # gerar dados para o mapara referente as semanas 25 e 26, período 14.06 a 27.06.for
                    # Se informar (-6,-6), será gerado dados referente à semana 21, período 17.05 - 23.05
                    'semana_a_considerar': (-1, 0)
                }
            }
        },
        'mapa_de_calor_casos_confirmados_semana_atual': {
            'titulo': 'Mapa de calor dos casos confirmados para COVID-19 (Semana atual)',
            'mapa': {
                'descricao': '',
                'tipo': TipoMapa.CALOR,
            },
            'fonte': {
                'funcao': 'indicadores.get_dados_mapa_calor',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    # semana_a_considerar indica o periodo de semana a ser considerada no filtro para obtenção dos dados
                    # Se (-1, 0) irá gerar dados da semana anterior a semana especificada no boletim + a semana especificada
                    # Exemplo: se o boletim é referente a semana 26 (21.06 - 27.06), o parâmetro (0, 1) irá
                    # gerar dados para o mapara referente as semanas 25 e 26, período 14.06 a 27.06.for
                    # Se informar (-6,-6), será gerado dados referente à semana 21, período 17.05 - 23.05
                    'semana_a_considerar': (0, 0)
                }
            }
        },
        'mapa_de_calor_casos_confirmados_semana_anterior_1': {
            'titulo': 'Mapa de calor dos casos confirmados para COVID-19 da 1a semana anterior',
            'mapa': {
                'descricao': '',
                'tipo': TipoMapa.CALOR,
            },
            'fonte': {
                'funcao': 'indicadores.get_dados_mapa_calor',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    # semana_a_considerar indica o periodo de semana a ser considerada no filtro para obtenção dos dados
                    # Se (-1, 0) irá gerar dados da semana anterior a semana especificada no boletim + a semana especificada
                    # Exemplo: se o boletim é referente a semana 26 (21.06 - 27.06), o parâmetro (0, 1) irá
                    # gerar dados para o mapara referente as semanas 25 e 26, período 14.06 a 27.06.for
                    # Se informar (-6,-6), será gerado dados referente à semana 21, período 17.05 - 23.05
                    'semana_a_considerar': (-1, -1)
                }
            }
        },
        'mapa_de_calor_casos_confirmados_semana_anterior_2': {
            'titulo': 'Mapa de calor dos casos confirmados para COVID-19 da 2a semana anterior',
            'mapa': {
                'descricao': '',
                'tipo': TipoMapa.CALOR,
            },
            'fonte': {
                'funcao': 'indicadores.get_dados_mapa_calor',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    # semana_a_considerar indica o periodo de semana a ser considerada no filtro para obtenção dos dados
                    # Se (-1, 0) irá gerar dados da semana anterior a semana especificada no boletim + a semana especificada
                    # Exemplo: se o boletim é referente a semana 26 (21.06 - 27.06), o parâmetro (0, 1) irá
                    # gerar dados para o mapara referente as semanas 25 e 26, período 14.06 a 27.06.for
                    # Se informar (-6,-6), será gerado dados referente à semana 21, período 17.05 - 23.05
                    'semana_a_considerar': (-2, -2)
                }
            }
        },
        'mapa_de_calor_casos_confirmados_semana_anterior_3': {
            'titulo': 'Mapa de calor dos casos confirmados para COVID-19 da 3a semana anterior',
            'mapa': {
                'descricao': '',
                'tipo': TipoMapa.CALOR,
            },
            'fonte': {
                'funcao': 'indicadores.get_dados_mapa_calor',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    # semana_a_considerar indica o periodo de semana a ser considerada no filtro para obtenção dos dados
                    # Se (-1, 0) irá gerar dados da semana anterior a semana especificada no boletim + a semana especificada
                    # Exemplo: se o boletim é referente a semana 26 (21.06 - 27.06), o parâmetro (0, 1) irá
                    # gerar dados para o mapara referente as semanas 25 e 26, período 14.06 a 27.06.for
                    # Se informar (-6,-6), será gerado dados referente à semana 21, período 17.05 - 23.05
                    'semana_a_considerar': (-3, -3)
                }
            }
        },
        'mapa_de_calor_casos_confirmados_semana_anterior_4': {
            'titulo': 'Mapa de calor dos casos confirmados para COVID-19 da 4a semana anterior',
            'mapa': {
                'descricao': '',
                'tipo': TipoMapa.CALOR,
            },
            'fonte': {
                'funcao': 'indicadores.get_dados_mapa_calor',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    # semana_a_considerar indica o periodo de semana a ser considerada no filtro para obtenção dos dados
                    # Se (-1, 0) irá gerar dados da semana anterior a semana especificada no boletim + a semana especificada
                    # Exemplo: se o boletim é referente a semana 26 (21.06 - 27.06), o parâmetro (0, 1) irá
                    # gerar dados para o mapara referente as semanas 25 e 26, período 14.06 a 27.06.for
                    # Se informar (-6,-6), será gerado dados referente à semana 21, período 17.05 - 23.05
                    'semana_a_considerar': (-4, -4)
                }
            }
        },
        'mapa_de_calor_casos_confirmados_semana_anterior_5': {
            'titulo': 'Mapa de calor dos casos confirmados para COVID-19 da 5a semana anterior',
            'mapa': {
                'descricao': '',
                'tipo': TipoMapa.CALOR,
            },
            'fonte': {
                'funcao': 'indicadores.get_dados_mapa_calor',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    # semana_a_considerar indica o periodo de semana a ser considerada no filtro para obtenção dos dados
                    # Se (-1, 0) irá gerar dados da semana anterior a semana especificada no boletim + a semana especificada
                    # Exemplo: se o boletim é referente a semana 26 (21.06 - 27.06), o parâmetro (0, 1) irá
                    # gerar dados para o mapara referente as semanas 25 e 26, período 14.06 a 27.06.for
                    # Se informar (-6,-6), será gerado dados referente à semana 21, período 17.05 - 23.05
                    'semana_a_considerar': (-5, -5)
                }
            }
        },
        'mapa_de_calor_casos_confirmados_semana_anterior_6': {
            'titulo': 'Mapa de calor dos casos confirmados para COVID-19',
            'mapa': {
                'descricao': '',
                'tipo': TipoMapa.CALOR,
            },
            'fonte': {
                'funcao': 'indicadores.get_dados_mapa_calor',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    # semana_a_considerar indica o periodo de semana a ser considerada no filtro para obtenção dos dados
                    # Se (-1, 0) irá gerar dados da semana anterior a semana especificada no boletim + a semana especificada
                    # Exemplo: se o boletim é referente a semana 26 (21.06 - 27.06), o parâmetro (0, 1) irá
                    # gerar dados para o mapara referente as semanas 25 e 26, período 14.06 a 27.06.for
                    # Se informar (-6,-6), será gerado dados referente à semana 21, período 17.05 - 23.05
                    'semana_a_considerar': (-6, -6)
                }
            }
        },
        'casos_descartados': {
            'titulo': 'Quantidade de casos descartados',
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Negativo',
                    },
                }
            }
        },
        'casos_suspeitos': {
            'titulo': 'Quantidade de casos suspeitos',
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': None,
                    },
                }
            }
        },
        'casos_confirmados': {
            'titulo': 'Quantidade de casos confirmados',
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                }
            }
        },
        'casos_notificados': {
            'titulo': 'Quantidade de casos notificados',
            'fonte': {
                'funcao': 'indicadores.get_casos',
            }
        },
        'casos_novos_casos_ultimos_7_dias': {
            'titulo': 'Quantidade de novos casos últimos 7 dias',
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {'dias_a_considerar': 7
                               }
            }
        },
        'total_recuperados': {
            'titulo': 'Total de recuperados',
            'fonte': {
                'funcao': 'indicadores.get_recuperados',
            }
        },
        'total_isolamento': {
            'titulo': 'Em acompanhamento',
            'fonte': {
                'funcao': 'indicadores.get_isolamento',
            }
        },
        'taxa_incidencia': {
            'titulo': 'Incidência acumulada / 100mil hab.',
            'fonte': {
                'funcao': 'indicadores.get_taxa_incidencia_acumulada',
            }
        },
        'taxa_letalidade': {
            'titulo': 'Taxa letalidade da COVID-19',
            'fonte': {
                'funcao': 'indicadores.get_taxa_letalidade',
            }
        },
        'taxa_mortalidade': {
            'titulo': 'Mortalidade/100mil hab',
            'fonte': {
                'funcao': 'indicadores.get_taxa_mortalidade',
            }
        },
        'inicio_semana_epi': {
            'titulo': 'Data de início da semana epidemiológica',
            'fonte': {
                'funcao': 'self.data_inicio_semana_epi'
            }
        },
        'fim_semana_epi': {
            'titulo': 'Data de fim da semana epidemiológica',
            'fonte': {
                'funcao': 'self.data_fim_semana_epi'
            }
        },
        'inicio_quinzena_epi': {
            'titulo': 'Data de início da quinzena epidemiológica',
            'fonte': {
                'funcao': 'self.data_inicio_quinzena_epi'
            }
        },
        'fim_quinzena_epi': {
            'titulo': 'Data de fim da quinzena epidemiológica',
            'fonte': {
                'funcao': 'self.data_fim_quinzena_epi'
            }
        },
        'grafico_num_casos_ocorrencia': {
            'titulo': 'Número de casos totais pelo município de ocorrêcia',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis':  {'title': {'text': 'Novos casos totais'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                }
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_num_casos_ocorrencia',
            }
        },
        'evolucao_casos_ocorrencia_valores_grafico_linha': {
            'titulo': 'Evolução dos casos totais',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Novos casos totais'}},
                    'xAxis': {'labels': {'rotation': 0, }},
                }
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_num_casos_ocorrencia_evolucao_valores',
            }
        },
        'evolucao_casos_ocorrencia_percentuais_grafico_linha': {
            'titulo': 'Percentuais de evolução dos casos totais',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Novos casos totais'}},
                    'xAxis': {'labels': {'rotation': -45, }},
                }

            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_num_casos_ocorrencia_evolucao_percentuais',
            }
        },
        'obitos_confirmados_dia_grafico_linha': {
            'titulo': 'Variáção de óbitos confirmados de COVID-19 por data',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Óbitos'}},
                    'xAxis': {'labels': {'rotation': -45, }},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                }
            },
            'fonte': {
                'funcao': 'indicadores.get_obitos',
                'parametros': {
                    'series_name': (('Data do óbito', 'data_do_obito'),),
                    'filter': {
                        'confirmado_covid19': True,
                    },
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                    'order_by': ['data_do_obito']
                }
            }
        },
        'obitos_confirmados_dia_grafico_coluna': {
            'titulo': 'Óbitos confirmados de COVID-19 por data do óbito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de Óbitos'}},
                    'xAxis': {
                        'type': 'datetime',
                        'labels': {'format': '{value:%Y-%b-%e %H:%m}'}
                    },
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                    'series': {'dataLabels': {'enabled': False}, },
                },
                'high_chars_series': [
                    {'type': 'sma',
                     # 'dashStyle': 'longdash',
                     'marker': {'enabled': False},
                     'color': 'blue',
                     'name': 'Média Móvel - 7  dias',
                     'linkedTo': 'Data do óbito',
                     'params': {
                         'period': 7,
                     }
                     },
                    {'type': 'sma',
                     # 'dashStyle': 'longdash',
                     'marker': {'enabled': False},
                     # 'zIndex': 1,
                     'color': 'black',
                     'name': 'Média Móvel - 15  dias',
                     'linkedTo': 'Data do óbito',
                     'params': {
                         'period': 15,
                     }
                     }
                ]
            },
            'fonte': {
                'funcao': 'indicadores.get_obitos',
                'parametros': {
                    'series_name': (('Data do óbito', 'data_do_obito'),),
                    'filter': {
                        'confirmado_covid19': True,
                    },
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                    'order_by': ['data_do_obito']
                }
            }
        },
        'obitos_confirmados_dia_acumulado_grafico_linha': {
            'titulo': 'Óbitos confirmados com covid-19 por data do óbito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Óbitos acumulados'}},
                    'colors': ['#046464', '#3c8989'],
                    'series': {'dataLabels': {'enabled': False}, },
                },
            },
            'fonte': {
                'funcao': 'indicadores.get_obitos',
                'parametros': {
                    'series_name': (('Data do óbito', 'data_do_obito'),),
                    'filter': {
                        'confirmado_covid19': True,
                    },
                    'acumulado': True,
                    'com_percentual_e_valor': False,
                    'order_by': ['data_do_obito']
                }
            }
        },
        'obitos_confirmados_semana_grafico_linha': {
            'titulo': 'Variação de óbitos confirmados com covid-19 por semana epidemiológica',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de Óbitos'}},
                    'colors': ['#046464', '#3c8989'],
                }
            },
            'fonte': {
                'funcao': 'indicadores.get_obitos_semana',
                'parametros': {
                    'series_name': (('Óbitos confirmados','data_semana'),),
                    'filter': {
                        'confirmado_covid19': True,
                    },
                    'acumulado': False,
                }
            }
        },
        'obitos_confirmados_semana_grafico_coluna': {
            'titulo': 'Óbitos confirmados de COVID-19 por Semana Epidemiológica por data de óbito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de Óbitos'}},
                    'colors': ['#046464', '#3c8989'],
                    'xAxis': {'labels': {'rotation': -45}},
                }
            },
            'fonte': {
                'funcao': 'indicadores.get_obitos_semana',
                'parametros': {
                    'series_name': (('Óbitos confirmados', 'data_semana'),),
                    'filter': {
                        'confirmado_covid19': True,
                    },
                    'acumulado': False,
                }
            }
        },
        'obitos_confirmados_semana_acumulado_grafico_linha': {
            'titulo': 'Óbitos confirmados com covid-19 por semana epidemiológica',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Óbitos acumulados'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'colors': ['#046464', '#3c8989'],
                    'series': {'dataLabels': {'enabled': False}, },
                }
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_obitos_semana',
                'parametros': {
                    'series_name': (('Semana do óbito','data_semana'),),
                    'filter': {
                        'confirmado_covid19': True,
                    },
                    'acumulado': True,
                }
            }
        },
        'casos_e_obitos_confirmados_distrito_grafico_coluna': {
            'titulo': 'Proporção de casos confirmados de Covid-19, por distrito sanitário no Município de Natal',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.AMBOS,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                    'series': {'dataLabels': {'rotation': 0}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos_confirmado_proporcao_distrito',
                'parametros': {
                    'com_percentual_e_valor': True,
                }
            }
        },

        'obitos_acumulados_confirmados_distrito_por_data_obito_grafico_linha': {
            'titulo': 'Óbitos confirmados acumulados de COVID-19 por data de óbito e por distrito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Óbitos acumulados'}},
                    'xAxis': {'labels': {'rotation': -45,}},
                    'series': {'dataLabels': {'enabled': False}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_obitos',
                'parametros': {
                    'series_name': (
                        ('Data do Óbito', 'data_do_obito'),
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': True,
                    'filter': {
                        'confirmado_covid19': True,
                    },
                }
            }
        },
        'obitos_acumulados_confirmados_distrito_por_semana_grafico_linha': {
            'titulo': 'Óbitos confirmado acumulados de COVID-19 por semana epidemiológica de data de óbito e por distrito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Óbitos acumulados'}},
                    'xAxis': {'labels': {'rotation': -45, }},
                    'series': {'dataLabels': {'enabled': False}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_obitos_semana',
                'parametros': {
                    'series_name': (
                        ('Semana do óbito', 'data_semana'),
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': True,
                    'filter': {
                        'confirmado_covid19': True,
                    },
                }
            }
        },
        'taxa_mortalidade_por_data_obito_grafico_linha': {
            'titulo': 'Taxa de mortalidade/100mil hab. de COVID-19 por data do óbito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Mortalidade/100mil hab.'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'enabled': False}},

                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_mortalidade',
                'parametros': {
                    'series_name': (
                        ('Mortalidade', 'data_do_obito'),
                    ),
                    'acumulado': True,
                    'filter': {
                        'confirmado_covid19': True,
                    },
                }
            }
        },
        'taxa_mortalidade_por_distrito_data_obito_grafico_linha': {
            'titulo': 'Taxa de mortalidade/100mil hab. de COVID-19 por distrito e data do óbito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Mortalidade/100mil hab.'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'enabled': False}},

                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_mortalidade',
                'parametros': {
                    'series_name': (
                        ('Mortalidade', 'data_do_obito'),
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': True,
                    'filter': {
                        'confirmado_covid19': True,
                    },
                }
            }
        },
        'taxa_mortalidade_distrito_grafico_coluna': {
            'titulo': 'Taxa de mortalidade/100mil hab. de COVID-19 por distrito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Mortalidade/100mil hab.'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'rotation': 0}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_mortalidade',
                'parametros': {
                    'series_name': (
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': False,
                    'filter': {
                        'confirmado_covid19': True,
                    },
                }
            }
        },
        'taxa_mortalidade_bairro_grafico_coluna': {
            'titulo': 'Taxa de mortalidade/100mil hab. de COVID-19 por bairro',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Mortalidade/100mil hab.'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'rotation': 0}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_mortalidade',
                'parametros': {
                    'series_name': (
                        ('Bairro', 'bairro__nome'),
                    ),
                    'acumulado': False,
                    'filter': {
                        'confirmado_covid19': True,
                    },
                }
            }
        },
        'mapa_mortalidade_por_bairro_endereco_moradia': {
            'titulo': 'Mapa do coeficiente de mortalidade de COVID-19 por bairro da residência de moradia',
            'mapa': {
                'descricao': '',
                'geojson': 'indicadores/static/js/Natal_Bairros2.geo.json',
                'tipo': TipoMapa.PADRAO,
                'valor': 'Taxa de mortalidade',
                'colunas': ['Bairro', 'Óbitos confirmados'],
                'mapeamento_colunas': ['code', 'value'],
                'mapeamento_valores': {'Bairro': {'SANTOS REIS': 'Santos Reis', 'ALECRIM': 'Alecrim'}},
                'dados_extra': {'categories': 'Bairro'}
            },
            'fonte': {
                'funcao': 'indicadores.get_taxa_mortalidade',
                'parametros': {
                    'series_name': (('Bairro', 'bairro__nome'),
                                    ('Resultado dos testes', 'resultado_do_teste_covid_19'),),
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                    'filter': {
                        'confirmado_covid19': True,
                    },
                    'dados_mapeamento': {
                        'resultado_do_teste_covid_19': {'Confirmado': 'Óbitos confirmados'},
                    },
                    'order_by': ['bairro__nome'],

                }
            }
        },
        'obitos_confirmados_distrito_grafico_coluna': {
            'titulo': 'Óbitos confirmados acumulado de COVID-19 por distrito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Óbitos acumulados'}},
                    'xAxis': {'labels': {'rotation': -45}},

                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_obitos',
                'parametros': {
                    'series_name': (
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': False,
                    'filter': {
                        'confirmado_covid19': True,
                    },
                }
            }
        },
        'obitos_confirmados_bairro_grafico_coluna': {
            'titulo': 'Óbitos confirmados de COVID-19 por bairro de residência',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Óbitos acumulados'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'rotation': 0, 'enabled': False}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_obitos',
                'parametros': {
                    'series_name': (
                        ('Bairro', 'bairro__nome'),
                    ),
                    'acumulado': False,
                    'filter': {
                        'confirmado_covid19': True,
                    },
                }
            }
        },
        'obitos_novos_confirmado_bairro_por_semana_anterior_5_grafico_linha': {
            'titulo': 'Óbitos novos confirmado de COVID-19 por por semana epidemiológica e por bairro de residência - últimas 6 semanas',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Óbitos Confirmados'}},
                    'xAxis': {'labels': {'rotation': -45, }, },
                    'series': {'dataLabels': {'enabled': False}},
                    'legend': {
                        'layout': 'vertical',
                        'align': 'right',
                        'verticalAlign': 'top',
                        'y': 30,
                        # 'navigation': {
                        #     'enabled': False
                        # },
                        # 'adjustChartSize': True,
                    },
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_obitos_semana',
                'parametros': {
                    'series_name': (
                        ('Bairro', 'bairro__nome'),
                        ('Semana do Óbito', 'data_semana'),
                    ),
                    'filter': {
                        'confirmado_covid19': True,
                    },
                    'acumulado': False,
                    'semana_a_considerar': (-5, 0)
                }
            }
        },


        'casos_confirmados_acumulados_por_data_notificacao_grafico_linha': {
            'titulo': 'Casos confirmados acumulados de COVID-19 por data de notificação',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Casos acumulados'}},
                    'series': {'marker': {'enabled': True, 'radius': 2}},
                    'xAxis': {'labels': {'rotation': -45, }},
                    'series': {'dataLabels': {'enabled': False}, },
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'series_name': (
                        ('Data de notificação', 'data'),),
                    'acumulado': True,
                    'order_by': ['data']
                }
            }
        },
        'casos_confirmados_por_data_notificacao_grafico_coluna': {
            'titulo': 'Casos confirmados novos de COVID-19 por data de notificação',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Casos novos'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                    'series': {'dataLabels': {'enabled': False},},
                },
                'high_chars_series' : [
                    {'type': 'sma',
                     # 'dashStyle': 'longdash',
                     'marker': {'enabled': False},
                     'color': 'blue',
                     'name': 'Média Móvel - 7  dias',
                     'linkedTo': 'Data da notificação',
                     'params': {
                         'period': 7,
                        }
                     },
                    {'type': 'sma',
                     # 'dashStyle': 'longdash',
                     'marker': {'enabled': False},
                     # 'zIndex': 1,
                     'color': 'black',
                     'name': 'Média Móvel - 15  dias',
                     'linkedTo': 'Data da notificação',
                     'params': {
                         'period': 15,
                        }
                     }
                ]
            },
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'series_name': (('Data da notificação', 'data'),),
                    'order_by': ['data'],
                }
            }
        },
        'casos_confirmados_por_semana_grafico_linha': {
            'titulo': 'Casos novos confirmados de COVID-19 por semana epidemiológica',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis':  {'title': {'text': 'Casos Novos'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                    'xAxis': {'labels': {'rotation': -45, }},
                }
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos_semana',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'series_name': (('Semana Epidemiológica', 'data_semana'),)
                }
            }
        },
        'casos_confirmados_por_semana_grafico_coluna': {
            'titulo': 'Casos novos confirmados de COVID-19 por Semana Epidemiológica de notificação',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Casos novos'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                },
            },
            'fonte': {
                'funcao': 'indicadores.get_casos_semana',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'series_name': (('Semana da notificação', 'data_semana'),),
                    'acumulado': False,
                }
            }
        },
        'casos_confirmados_acumulados_por_semana_grafico_linha': {
            'titulo': 'Casos confirmados acumulados de COVID-19 por Semana Epidemiológica de notificação',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Casos acumulados'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                    'xAxis': {'labels': {'rotation': -45, }},
                    'series': {'dataLabels': {'enabled': False}, },
                }
            },
            'fonte': {
                'funcao': 'indicadores.get_casos_semana',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'series_name': (('Semana da notificação', 'data_semana'),),
                    'acumulado': True,
                }
            }
        },
        'casos_acumulados_confirmados_distrito_por_data_notificacao_grafico_linha': {
            'titulo': 'Casos confirmado acumulados de COVID-19 por data de notificação e por distrito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Casos acumulados'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'enabled': False}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (
                        ('Data da Notificação', 'data'),
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': True,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'exclude': {
                        'bairro': None,
                    },
                }
            }
        },
        'casos_acumulados_confirmados_distrito_por_semana_notificacao_grafico_linha': {
            'titulo': 'Casos confirmado acumulados de COVID-19 por semana epidemiológica de notificação e por distrito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Casos acumulados'}},
                    'series': {'dataLabels': {'enabled': False}},

                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos_semana',
                'parametros': {
                    'series_name': (
                        ('Semana da notificação', 'data_semana'),
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': True,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'exclude': {
                        'bairro': None,
                    },
                }
            }
        },
        'casos_confirmados_distrito_grafico_coluna': {
            'titulo': 'Casos confirmados acumulado de COVID-19 por distrito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Casos acumulados'}},
                    'xAxis': {'labels': {'rotation': -45}},

                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': False,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'exclude': {
                        'bairro': None,
                    },
                }
            }
        },
        'taxa_incidencia_acumulada_por_data_notificacao_grafico_linha': {
            'titulo': 'Taxa de Incidência/100mil hab. de COVID-19 por data de notificação',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Incidência/100mil hab.'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'enabled': False}},

                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_incidencia_acumulada',
                'parametros': {
                    'series_name': (
                        ('Incidência', 'data'),
                    ),
                    'acumulado': True,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'exclude': {
                        'bairro': None,
                    },
                }
            }
        },
        'taxa_incidencia_acumulada_distrito_por_data_notificacao_grafico_linha': {
            'titulo': 'Taxa de Incidência/100mil hab. de COVID-19 por distrito e data de notificação',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Incidência/100mil hab.'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'enabled': False}},

                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_incidencia_acumulada',
                'parametros': {
                    'series_name': (
                        ('Incidência', 'data'),
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': True,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'exclude': {
                        'bairro': None,
                    },
                }
            }
        },
        'taxa_incidencia_distrito_grafico_coluna': {
            'titulo': 'Taxa de Incidência/100mil hab. de COVID-19 por distrito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Incidência/100mil hab.'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'rotation': 0}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_incidencia_acumulada',
                'parametros': {
                    'series_name': (
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': False,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                }
            }
        },
        'taxa_incidencia_bairro_grafico_coluna': {
            'titulo': 'Taxa de Incidência/100mil hab. de COVID-19 por bairro',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Incidência/100mil hab.'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'rotation': 0, 'enabled': False}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_incidencia_acumulada',
                'parametros': {
                    'series_name': (
                        ('Bairro', 'bairro__nome'),
                    ),
                    'acumulado': False,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                }
            }
        },
        'mapa_incidencia_por_bairro_endereco_moradia': {
            'titulo': 'Mapa de coeficiente de incidência de COVID-19 por bairro da residência de moradia',
            'mapa': {
                'descricao': '',
                'geojson': 'indicadores/static/js/Natal_Bairros2.geo.json',
                'tipo': TipoMapa.PADRAO,
                'valor': 'Taxa de Incidência',
                'colunas': ['Bairro', 'Casos confirmados'],
                'mapeamento_colunas': ['code', 'value'],
                'mapeamento_valores': {'Bairro': {'SANTOS REIS': 'Santos Reis', 'ALECRIM': 'Alecrim'}},
                'dados_extra': {'categories': 'Bairro'}
            },
            'fonte': {
                'funcao': 'indicadores.get_taxa_incidencia_acumulada',
                'parametros': {
                    'series_name': (('Bairro', 'bairro__nome'),
                                    ('Resultado dos testes', 'dados__resultado_do_teste'),),
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                    'dados_mapeamento': {
                        'dados__resultado_do_teste': {'Negativo': 'Descartado', 'Positivo': 'Casos confirmados',
                                                             None: 'Suspeito'}},
                    'order_by': ['bairro__nome'],
                }
            }
        },
        # 'casos_acumulados_confirmados_bairro_por_data_notificacao_grafico_linha': {
        #     'titulo': 'Casos acumulados de COVID-19 por data de notificação e por bairro',
        #     'grafico': {
        #         'descricao': '',
        #         'tipo': TipoVisualizacao.LINHA,
        #         'valor_forma_exibicao': ValorFormaExbicao.VALOR,
        #         'high_chart_option': {
        #             'yAxis': {'title': {'text': 'Casos acumulados'}},
        #             'xAxis': {'labels': {'rotation': -45}},
        #
        #         },
        #     },
        #     'mapa': None,
        #     'fonte': {
        #         'funcao': 'indicadores.get_casos',
        #         'parametros': {
        #             'series_name': (
        #                 ('Data da Notificação', 'data'),
        #                 ('Bairro', 'bairro__nome'),
        #             ),
        #             'acumulado': True,
        #             'filter': {
        #                 'dados__resultado_do_teste': 'Positivo',
        #             },
        #             'exclude': {
        #                 'bairro': None,
        #             },
        #         }
        #     }
        # },
        'taxa_letalidade_por_data_grafico_linha': {
            'titulo': 'Taxa de letalidade da COVID-19 por data',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Taxa de letalidade'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'enabled': False}},

                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_letalidade',
                'parametros': {
                    'series_name': (
                        ('Letalidade', 'data'),
                    ),
                    'acumulado': True,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                }
            }
        },
        'taxa_letalidade_distrito_data_grafico_linha': {
            'titulo': 'Taxa de letalidade da COVID-19 por distrito e data',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'Taxa de letalidade'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'enabled': False}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_letalidade',
                'parametros': {
                    'series_name': (
                        ('Letalidade', 'data'),
                        ('Distrito', 'bairro__distrito__nome'),
                    ),
                    'acumulado': True,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                }
            }
        },
        'taxa_letalidade_distrito_grafico_coluna': {
            'titulo': 'Taxa de letalidade da COVID-19 por distrito',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Taxa de letalidade'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'rotation': 0}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_letalidade',
                'parametros': {
                    'series_name': (
                        ('Letalidade', 'bairro__distrito__nome'),
                    ),
                    'acumulado': False,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                }
            }
        },
        'taxa_letalidade_bairro_grafico_coluna': {
            'titulo': 'Taxa de letalidade da COVID-19 por bairro',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Taxa de letalidade'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels': {'rotation': 0}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_taxa_letalidade',
                'parametros': {
                    'series_name': (
                        ('Bairro', 'bairro__nome'),
                    ),
                    'acumulado': False,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                }
            }
        },

        'casos_novos_confirmado_bairro_por_semana_anterior_5_grafico_linha': {
            'titulo': 'Casos novos confirmado de COVID-19 por por semana epidemiológica e por bairro de residência - últimas 6 semanas',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Casos Confirmados'}},
                    'xAxis': {'labels': {'rotation': -45,},},
                    'series': {'dataLabels': {'enabled': False}},
                    'legend': {
                        'layout': 'vertical',
                        'align': 'right',
                        'verticalAlign': 'top',
                        'y': 30,
                        # 'navigation': {
                        #     'enabled': False
                        # },
                        # 'adjustChartSize': True,
                    },
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos_semana',
                'parametros': {
                    'series_name': (
                        ('Bairro', 'bairro__nome'),
                        ('Semana da notificação', 'data_semana'),
                    ),
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'acumulado': False,
                    'exclude': {
                        'bairro': None,
                    },
                    'semana_a_considerar': (-5, 0)
                }
            }
        },
        'casos_confirmados_bairro_grafico_coluna': {
            'titulo': 'Casos confirmados de COVID-19 por bairro de residência',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Casos acumulados'}},
                    'xAxis': {'labels': {'rotation': -45}},
                    'series': {'dataLabels':{'enabled': False}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (
                        ('Bairro', 'bairro__nome'),
                    ),
                    'acumulado': False,
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'exclude': {
                        'bairro': None,
                    },
                }
            }
        },
        'casos_confirmados_sexo_idade_grafico_colunastaking': {
            'titulo': 'Proporção dos casos de Covid-19 por sexo e faixa etária, em Natal',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA_STAKING,
                'valor_forma_exibicao': ValorFormaExbicao.AMBOS,
                'high_chart_option': {
                    'yAxis':  {'title': {'text': 'Número de casos'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                    'series': {'dataLabels': {'rotation': 0}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos_confirmado_proporcao_sexo_idade',
                'parametros': {}
            }
        },
        'casos_confirmados_doencas_preexistentes_grafico_coluna': {
            'titulo': 'Proporção dos casos confirmados de Covid-19 por doenças preexistentes, em Natal',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis':  {'title': {'text': 'Número de casos confirmados'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos_confirmado_proporcao_doencas_preexistentes',
                'parametros': {
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'com_percentual_e_valor': True,
                }

            }
        },
        'casos_confirmados_raca_grafico_coluna': {
            'titulo': 'Proporção dos casos de Covid-19 por raça, em Natal',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis':  {'title': {'text': 'Número de casos confirmados'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Raça', 'dados__raca_cor'),),
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'acumulado': False,
                    'com_percentual_e_valor': True,
                    'order_by': ['dados__raca_cor']
                }
            }
        },
        'notificacoes_raca_grafico_coluna': {
            'titulo': 'Proporção das notificações de Covid-19 por raça, em Natal',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis':  {'title': {'text': 'Número de casos confirmados'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Raça', 'dados__raca_cor'),),
                    'acumulado': False,
                    'com_percentual_e_valor': True,
                    'order_by': ['dados__raca_cor']
                }
            }
        },
        # 'grafico_ocupacao_leitos_fixo': {
        #     'titulo': 'Proporção de ocupação de leitos por estabelecimento de saúde, em Natal',
        #     'grafico': {
        #         'descricao': '',
        #         'tipo': TipoVisualizacao.COLUNA_STAKING,
        #         'valor_forma_exibicao': ValorFormaExbicao.AMBOS,
        #         'high_chart_option': {
        #             'yAxis':  {'title': {'text': 'Percentual'}},
        #             'colors': ['#046464', '#3c8989'],
        #         },
        #     },
        #     'mapa': None,
        #     'fonte': {
        #         'funcao': 'indicadores.get_percentual_ocupacao_leitos_fixo',
        #         'parametros': {}
        #     }
        # },
        'obitos_confirmados_sexo_idade_grafico_colunastaking': {
            'titulo': ' Proporção dos casos de Covid-19 por sexo e faixa etária',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA_STAKING,
                'valor_forma_exibicao': ValorFormaExbicao.AMBOS,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_obitos_confirmado_proporcao_sexo_idade',
                'parametros': {}
            }
        },
        'casos_confirmados_por_tipo_teste_grafico_pizza': {
            'titulo': 'Proporção dos casos de Covid-19 por tipo de teste, em Natal',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos confirmados'}},
                    'colors': ['#046464', '#3c8989'],
                    'chart': {'height': 280},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Tipo de Teste', 'dados__tipo_de_teste'),),
                    'filter': {
                        'dados__resultado_do_teste': 'Positivo',
                    },
                    'acumulado': False,
                    'com_percentual_e_valor': True,
                    'order_by': ['dados__tipo_de_teste']
                }
            }
        },
        'resultado_dos_testes_por_tipo_grafico_pizza': {
            'titulo': 'Gráfico resultado dos testes tipo',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Resultado dos testes', 'dados__resultado_do_teste'),),
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                    'dados_mapeamento': {
                        'dados__resultado_do_teste': {'Negativo': 'Descartado', 'Positivo': 'Confirmado',
                                                             None: 'Suspeito'}},
                }
            }
        },
        'resultado_dos_testes_por_data_tipo_grafico_linha': {
            'titulo': 'Gráfico resultado dos testes por data e tipo',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.AMBOS,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}},
                    'series': {'dataLabels': {'enabled': False}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Casos notificados', 'data'),
                    ('Resultado dos testes', 'dados__resultado_do_teste'),),
                    'acumulado': True,
                    'com_percentual_e_valor': False,
                    'dados_mapeamento': {'dados__resultado_do_teste': {'Negativo': 'Descartado', 'Positivo': 'Confirmado', None: 'Suspeito'}},
                    'order_by': ['data']
                }
            }
        },
        'resultado_dos_testes_por_bairro_tipo_grafico_colunastaking': {
            'titulo': 'Gráfico resultado dos testes por bairro e tipo',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA_STAKING,
                'valor_forma_exibicao': ValorFormaExbicao.AMBOS,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}},
                    'series': {'dataLabels': {'enabled': False}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Bairro', 'bairro__nome'),
                    ('Resultado dos testes', 'dados__resultado_do_teste'),),
                    'acumulado': False,
                    'com_percentual_e_valor': True,
                    'dados_mapeamento': {'dados__resultado_do_teste': {'Negativo': 'Descartado', 'Positivo': 'Confirmado', None: 'Suspeito'}},
                    'order_by': ['bairro__nome']
                }
            }
        },
        'tabela_resultado_dos_testes_por_bairro_tipo': {
            'titulo': 'Tabela de resultado dos testes por bairro e tipo',
            'tabela': {
                'descricao': '',
                'colunas': ['Bairro', 'Casos confirmados', 'Casos descartados', 'Casos suspeitos'],
                'classes': 'table table-bordered',
                'dados_extra': {'categories': 'Bairro'}
            },
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Bairro', 'bairro__nome'),
                    ('Resultado dos testes', 'dados__resultado_do_teste'),),
                    'acumulado': True,
                    'com_percentual_e_valor': False,
                    'dados_mapeamento': {'dados__resultado_do_teste': {'Negativo': 'Casos descartados', 'Positivo': 'Casos confirmados', None: 'Casos suspeitos'}},
                    'order_by': ['bairro__nome'],
                }
            }
        },
        'evolucao_caso_por_data_tipo_grafico_linha': {
            'titulo': 'Gráfico evolução de caso por data e tipo',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.AMBOS,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Casos notificados', 'data'),
                                    ('Evolução dos casos', 'dados__evolucao_caso'),),
                    'acumulado': True,
                    'com_percentual_e_valor': False,
                    'order_by': ['data']
                }
            }
        },
        'evolucao_caso_testes_por_tipo_grafico_pizza': {
            'titulo': 'Gráfico resultado dos testes por tipo',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Evolução dos casos', 'dados__evolucao_caso'),),
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                }
            }
        },
        'estado_do_teste_por_data_tipo_grafico_linha': {
            'titulo': 'Gráfico situação dos testes por data e tipo',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.LINHA,
                'valor_forma_exibicao': ValorFormaExbicao.AMBOS,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}},
                    'series': {'dataLabels': {'enabled': False}},
                },
            },
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Casos notificados', 'data'),
                                    ('Estado do teste', 'dados__estado_do_teste'),),
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                    'order_by': ['data']
                }
            }
        },
        'estado_do_teste_por_tipo_grafico_pizza': {
            'titulo': 'Gráfico situação dos testes tipo',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Estado do teste', 'dados__estado_do_teste'),),
                    'acumulado': False,
                    'com_percentual_e_valor': False,
                }
            }
        },

        'id1': {
            'titulo': 'Proporção dos casos por sexo e resultado do teste',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA_STAKING,
                'valor_forma_exibicao': ValorFormaExbicao.AMBOS,
                'high_chart_option': {
                    'yAxis':  {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Resultado dos testes', 'dados__resultado_do_teste'), ('Sexo', 'dados__sexo')),
                    'dados_mapeamento': {
                        'dados__resultado_do_teste': {'Negativo': 'Descartado', 'Positivo': 'Confirmado', None: 'Suspeito'},
                        'dados__sexo': {'Feminino': 'Mulher', 'Masculino': 'Homem',  None: 'Não Informado'}
                    },
                }
            }
        },
        'id2': {
            'titulo': 'Proporção dos casos por sexo e resultado do teste',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.AMBOS,
                'high_chart_option': {
                    'yAxis':  {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Resultado dos testes', 'dados__resultado_do_teste'), ('Sexo', 'dados__sexo'))
                }
            }
        },
        'id3': {
            'titulo': 'Proporção dos casos por sexo',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis':  {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {'series_name': (('Sexo', 'dados__sexo'),)
                               }
            }
        },
        # 'id4': {
        #     'titulo': 'Notificações por mês e resultado de teste ',
        #     'grafico': {
        #         'descricao': '',
        #         'tipo': TipoVisualizacao.LINHA,
        #         'valor_forma_exibicao': ValorFormaExbicao.VALOR,
        #         'high_chart_option': {
        #             'yAxis':  {'title': {'text': 'Número de casos'}}
        #         },
        #     },
        #     'mapa': None,
        #     'fonte': {
        #         'funcao': 'indicadores.get_casos',
        #         'parametros': {
        #             'series_name': (('Data da Notificação', 'data__month'),
        #                             ('Resultado do teste', 'dados__resultado_do_teste'),),
        #             'order_by': ['data']
        #         }
        #     }
        # },
        'id5': {
            'titulo': 'Notificações por tipo de resultado do teste',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis':  {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Resultado do teste', 'dados__resultado_do_teste'),),
                    'dados_mapeamento': {
                        'dados__resultado_do_teste': {'Negativo': 'Descartado', 'Positivo': 'Confirmado', None: 'Suspeito'},
                    },
                }
            }
        },
        'id6': {
            'titulo': 'Número de casos por cbo',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.COLUNA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}},
                    'xAxis': {'labels': {'rotation': -45}},

                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('CBO', 'dados__cbo'),),
                    'exclude': {'dados__cbo': None,
                                },
                }
            }
        },
        'id8': {
            'titulo': 'Casos de notificações por tosse',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}},
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    # 'filter': {
                    #     'dados__resultado_do_teste': 'Positivo',
                    # },
                    'series_name': (
                        ('Sintomas Tosse ', 'dados__tosse'),
                    ),
                    # 'acumulado': True,
                }
            }
        },
        'id10': {
            'titulo': 'Notificações por Sintoma - Dispnéia ',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Casos com Dispnéia', 'dados__dispneia'),),
                    'dados_mapeamento': {'dados__dispneia': {'Sim': 'Com dispnéia',
                                         'Não': 'Sem dispnéia',
                                         None: 'Não informaro'
                                         }
                                         }
                }
            }
        },
        'id11': {
            'titulo': 'Notificações por Sintoma - Febre ',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Casos com Febre', 'dados__febre'),),
                    'dados_mapeamento': {'dados__febre':{'Sim': 'Com Febre',
                                         'Não': 'Sem Febre',
                                         None: 'Não informaro'
                                         }
                                         }
                }
            }
        },
        'id12': {
            'titulo': 'Notificações por Sintoma - Tosse ',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Casos com Tosse', 'dados__tosse'),),
                    'dados_mapeamento': {'dados__tosse': {'Sim': 'Com Tosse',
                                         'Não': 'Sem Tosse',
                                         None: 'Não informaro'
                                         }
                                         }
                }
            }
        },
        'id13': {
            'titulo': 'Notificações por Sintoma - Diabetes ',
            'grafico': {
                'descricao': '',
                'tipo': TipoVisualizacao.PIZZA,
                'valor_forma_exibicao': ValorFormaExbicao.VALOR,
                'high_chart_option': {
                    'yAxis': {'title': {'text': 'Número de casos'}}
                },
            },
            'mapa': None,
            'fonte': {
                'funcao': 'indicadores.get_casos',
                'parametros': {
                    'series_name': (('Casos com Diabetes', 'dados__diabetes'),),
                    'dados_mapeamento': {'dados__diabetes': {'Sim': 'Com Diabetes',
                                         'Não': 'Sem Diabetes',
                                         None: 'Não informaro'
                                         }}
                }
            }
        },
        'tabela_casos_e_obitos_por_bairro': {
            'titulo': 'Tabela de casos e óbitos por bairro',
            'tabela': {
                'descricao': '',
                'colunas': ['Bairro', 'Casos confirmados', 'Óbitos'],
                'classes': 'table table-bordered',
                'dados_extra': {'categories': 'Bairro'}
            },
            'fonte': {
                'funcao': 'indicadores.get_casos_e_obitos_por_bairro',
            }
        },
        'tabela_sintese_casos_obitos_incidencia_mortalidade_por_bairo': {
            'titulo': 'Tabela de casos e óbitos por bairro',
            'tabela': {
                'descricao': '',
                'colunas': ['Bairro', 'Casos confirmados', 'Óbitos'],
                'classes': 'table table-bordered',
                'dados_extra': {'categories': 'Bairro'}
            },
            'fonte': {
                'funcao': 'indicadores.get_casos_e_obitos_por_bairro',
            }
        },
        'tabela_sintese_casos_obitos_incidencia_mortalidade_por_distrito': {
            'titulo': 'Tabela de casos e óbitos por bairro',
            'tabela': {
                'descricao': '',
                'colunas': ['Bairro', 'Casos confirmados', 'Óbitos'],
                'classes': 'table table-bordered',
                'dados_extra': {'categories': 'Bairro'}
            },
            'fonte': {
                'funcao': 'indicadores.get_casos_e_obitos_por_bairro',
            }
        },
        # 'grafico_casos_acumulados_confirmados_por_data_Notificação': {
        #     'titulo': 'Gráfico de casos confirmados acumulados por data de notificação',
        #     'grafico': {
        #         'descricao': '',
        #         'tipo': TipoVisualizacao.LINHA,
        #         'valor_forma_exibicao': ValorFormaExbicao.VALOR,
        #         'high_chart_option': {
        #             'yAxis':  {'title': {'text': 'Número de casos'}},
        #             'colors': ['#046464', '#3c8989'],
        #             'chart': {'height': 280},
        #         }
        #     },
        #     'fonte': {
        #         'funcao': 'indicadores.get_casos',
        #         'parametros': {
        #             'filter': {
        #                 'dados__resultado_do_teste': 'Positivo',
        #             },
        #             'series_name': (('Casos notificados', 'data'),),
        #             'acumulado': True,
        #             'order_by': ['data']
        #         }
        #     }
        # },
    }
    if chave is None:
        return collections.OrderedDict(sorted(dic_catalogo.items()))
    return dic_catalogo[chave]
