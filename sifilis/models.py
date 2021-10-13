from django.conf import settings
from django.db import models
from django.db.models import Q
from djchoices import DjangoChoices, ChoiceItem


class CID(models.Model):
    # TODO: vai pra base
    codigo = models.CharField('Código', max_length=255, unique=True)
    nome = models.CharField('Nome', max_length=255, unique=True)

    class Meta:
        ordering = ['codigo']

    def __str__(self):
        return f'{self.codigo}: {self.nome}'


class Medicamento(models.Model):
    nome = models.CharField('Nome', max_length=255)
    solucao = models.CharField('Solução', max_length=255)
    metodo = models.CharField('Método', max_length=255)

    class Meta:
        ordering = ['nome', 'solucao', 'metodo']
        unique_together = ['nome', 'solucao', 'metodo']

    def __str__(self):
        return self.nome


class PlanoTerapeutico(models.Model):
    restrito_ao_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    # NOTA: restrito_ao_usuario indica que o plano terapêutico só estará disponível para tal usuário, sendo
    #  algo que ele mesmo cadastrou e não faz parte da "base de conhecimento comum"
    nome = models.CharField('Nome', max_length=255)
    cid = models.ManyToManyField(CID)
    medicamento = models.ForeignKey(Medicamento, on_delete=models.PROTECT)
    orientacao = models.TextField('Orientação')
    qtd_doses = models.PositiveIntegerField(default=1)
    invervalo_entre_doses_em_horas = models.PositiveIntegerField(default=0)
    prazo_extra_em_horas = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['nome']
        unique_together = ('nome', 'medicamento', 'orientacao', 'qtd_doses', 'invervalo_entre_doses_em_horas', 'prazo_extra_em_horas')
        verbose_name = 'Plano Terapêutico'
        verbose_name_plural = 'Planos Terapêuticos'

    def __str__(self):
        return self.nome

    def get_invervalo_entre_doses_em_horas_display(self):
        if not self.invervalo_entre_doses_em_horas:
            return 'Dose única'
        elif self.invervalo_entre_doses_em_horas > 24:
            dias = int(self.invervalo_entre_doses_em_horas / 24)
            horas = self.invervalo_entre_doses_em_horas % 24
            val = f'1 dose a cada {dias} dias'
            if horas:
                val += f' e {horas} horas'
            return val
        else:
            return f'1 dose a cada {self.invervalo_entre_doses_em_horas} horas'

    def get_prazo_extra_em_dias(self):
        dias = int(self.prazo_extra_em_horas / 24)
        horas = self.prazo_extra_em_horas % 24
        val = f'{dias} dias'
        if horas:
            val += f' e {horas} horas'
        return val

    @staticmethod
    def qs_visiveis(user):
        return PlanoTerapeutico.objects.filter(
            Q(restrito_ao_usuario__isnull=True) | Q(restrito_ao_usuario=user)).distinct()


class TipoExame(models.Model):
    nome = models.CharField('Nome', max_length=255, unique=True)

    class Meta:
        verbose_name = 'Tipo de Exame'
        verbose_name_plural = 'Tipos de Exame'

    def __str__(self):
        return self.nome


class TipoExameResultado(models.Model):
    tipo_de_exame = models.ForeignKey(TipoExame, on_delete=models.PROTECT)
    nome = models.CharField('Nome', max_length=255)

    class Meta:
        verbose_name = 'Possível Resultado para Tipo de Exame'
        verbose_name_plural = 'Possíveis Resultados para Tipo de Exame'
        unique_together = ('tipo_de_exame', 'nome')

    def __str__(self):
        return self.nome


class Exame(models.Model):
    paciente = models.ForeignKey('base.PessoaFisica', on_delete=models.PROTECT, related_name='sifilis_exame_set')
    data_de_realizacao = models.DateTimeField(verbose_name='Data da realização')
    resultado = models.ForeignKey(TipoExameResultado, on_delete=models.PROTECT)
    observacoes = models.TextField(verbose_name='Observações')


class Relacionamento(models.Model):

    class TiposDeRelacionamento(DjangoChoices):
        pai = ChoiceItem('pai', "Pai")
        mae = ChoiceItem('mae', "Mãe")

    paciente = models.ForeignKey('base.PessoaFisica', on_delete=models.PROTECT, related_name='sifilis_relacionamento_set')
    pessoa = models.ForeignKey('base.PessoaFisica', on_delete=models.PROTECT, related_name='pessoanucleointimoset')
    tipo_de_relacionamento = models.CharField(
        max_length=255, choices=TiposDeRelacionamento.choices)

    class Meta:
        unique_together = ('paciente', 'pessoa')


class PlanoTerapeuticoPaciente(models.Model):

    class Situacoes(DjangoChoices):
        em_andamento = ChoiceItem("em_andamento", "Em andamento")
        finalizado = ChoiceItem("finalizado", "Finalizado")
        suspenso = ChoiceItem("suspenso", "Suspenso")

    paciente = models.ForeignKey('base.PessoaFisica', on_delete=models.PROTECT, related_name='sifilis_planoterapeutico_set')
    plano_terapeutico = models.ForeignKey(PlanoTerapeutico, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    situacao = models.CharField(
        'Situação', max_length=255, choices=Situacoes.choices, default=Situacoes.em_andamento)

    def finalizar(self):
        if not self.estah_em_andamento():
            raise ValueError()
        self.situacao = self.Situacoes.finalizado
        self.save()

    def suspender(self):
        if not self.estah_em_andamento():
            raise ValueError()
        self.situacao = self.Situacoes.suspenso
        self.save()

    def estah_em_andamento(self):
        return self.situacao == self.Situacoes.em_andamento

    def registrar_dose(self, dose_aplicada_em):
        if not self.estah_em_andamento():
            raise ValueError()
        DoseAplicada.objects.create(
            plano_terapeutico_paciente=self,
            dose_aplicada_em=dose_aplicada_em,
        )


class DoseAplicada(models.Model):
    plano_terapeutico_paciente = models.ForeignKey(PlanoTerapeuticoPaciente, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    dose_aplicada_em = models.DateTimeField()


class Antecedente(models.Model):

    class Situacoes(DjangoChoices):
        teve = ChoiceItem("teve", "Já teve a doença")
        tem = ChoiceItem("tem", "Está atualmente com a doença")
        nao_tem = ChoiceItem("nao_tem", "Não tem a doença")

    paciente = models.ForeignKey('base.PessoaFisica', on_delete=models.PROTECT, related_name='sifilis_antecedente_set')
    cid = models.ForeignKey(CID, on_delete=models.PROTECT)
    situacao = models.CharField(
        max_length=255, choices=Situacoes.choices, verbose_name='Situação')

    def get_cids(self):
        nomes = list()
        for cid in self.cid.all():
            nomes.append(cid.nome)
        return ', '.join(nomes)

def get_historico(paciente):
    # TODO: retornar exames e planos terapeuticos relacionados ao paciente?
    #  Creio que isso não será, necessariamente, um modelo
    return []

# TODO: solução global para Logs
# TODO: criar forms.py e mover forms pra lá
