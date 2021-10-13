from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import DetailView

from base.models import PessoaFisica
from . import forms, models
from .dados_iniciais import importar_dados_iniciais
from .forms import ExamePasso2Form, ExamePasso1Form, RelacionamentoForm, AntecedenteForm

from .models import Antecedente


class DadosPessoaView(DetailView):
    model = PessoaFisica
    context_object_name = 'pessoa'
    template_name = 'sifilis/pessoa.html'


def adicionar_plano_terapeutico_passo_1(request, pessoa_pk):
    importar_dados_iniciais()  # TODO: mover para migrations num RunPython
    pessoa = PessoaFisica.objects.get(pk=pessoa_pk)
    passo = 1
    passo_descricao = 'Por favor, informe o CID'
    form = forms.Passo1Form(request.POST or None)
    if form.is_valid():
        cid_pk = form.cleaned_data['cid'].pk
        return HttpResponseRedirect(reverse('sifilis:adicionar_plano_terapeutico_passo_2', args=[pessoa_pk, cid_pk]))
    return render(request, 'sifilis/adicionar_plano_terapeutico.html', locals())


def adicionar_plano_terapeutico_passo_2(request, pessoa_pk, cid_pk):
    pessoa = PessoaFisica.objects.get(pk=pessoa_pk)
    qs_cdi = models.CID.objects.all()
    passo = 2
    passo_descricao = 'Por favor, informe o plano terapêtico'
    cid = models.CID.objects.get(pk=cid_pk)
    form = forms.Passo2Form(data=request.POST or None, user=request.user, cid=cid, pessoa=pessoa)
    planos_terapeuticos = form.fields['plano_terapeutico'].queryset
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse('sifilis:listar_por_pessoa', args=[pessoa_pk]))
    return render(request, 'sifilis/adicionar_plano_terapeutico.html', locals())


def adicionar_novo_plano_terapeutico_e_vincular_ao_paciente(request, pessoa_pk, cid_pk):
    passo = 3  # TODO: mudar nomenclatura, já que isso não é passo
    passo_descricao = 'Cadastre os dados do plano terapêutico'
    pessoa = PessoaFisica.objects.get(pk=pessoa_pk)
    cid = models.CID.objects.get(pk=cid_pk)
    form = forms.CadastrarPlanoEVincularAoPacienteForm(
        data=request.POST or None, user=request.user, cid=cid, pessoa=pessoa)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse('sifilis:listar_por_pessoa', args=[pessoa_pk]))
    return render(request, 'sifilis/adicionar_plano_terapeutico.html', locals())


def plano_terapeutico_paciente_view(request, pk):
    object = models.PlanoTerapeuticoPaciente.objects.get(pk=pk)
    form_registrar_dose = forms.RegistrarDoseForm(
        data=request.POST or None, plano_terapeutico_paciente=object)
    if form_registrar_dose.is_valid():
        form_registrar_dose.save()
        return HttpResponseRedirect(reverse('sifilis:plano_terapeutico_paciente', args=[pk]))
    return render(request, 'sifilis/plano_terapeutico_paciente.html', locals())


def plano_terapeutico_paciente_finalizar(request, pk):
    object = models.PlanoTerapeuticoPaciente.objects.get(pk=pk)
    object.finalizar()
    messages.success(request, 'Operação realizada com sucesso!')
    return HttpResponseRedirect(reverse('sifilis:plano_terapeutico_paciente', args=[pk]))


def plano_terapeutico_paciente_suspender(request, pk):
    object = models.PlanoTerapeuticoPaciente.objects.get(pk=pk)
    object.suspender()
    messages.success(request, 'Operação realizada com sucesso!')
    return HttpResponseRedirect(reverse('sifilis:plano_terapeutico_paciente', args=[pk]))


def adicionar_exame_passo_1(request, pessoa_pk):
    importar_dados_iniciais()  # TODO: mover para migrations num RunPython
    pessoa = PessoaFisica.objects.get(pk=pessoa_pk)
    passo = 1
    passo_descricao = 'Por favor, informe o Tipo de Exame'
    form = ExamePasso1Form(request.POST or None)
    if form.is_valid():
        tipoexame_pk = form.cleaned_data['tipoexame'].pk
        return HttpResponseRedirect(reverse('sifilis:adicionar_exame_passo_2', args=[pessoa_pk, tipoexame_pk]))
    return render(request, 'sifilis/adicionar_exame.html', locals())


def adicionar_exame_passo_2(request, pessoa_pk, tipoexame_pk):
    pessoa = PessoaFisica.objects.get(pk=pessoa_pk)
    passo = 2
    passo_descricao = 'Por favor, informe o resultado do exame'
    tipo_exame = models.TipoExame.objects.get(pk=tipoexame_pk)
    form = ExamePasso2Form(data=request.POST or None, user=request.user, tipo_exame=tipo_exame, pessoa=pessoa)
    if form.is_valid():
        o = form.save(False)
        o.paciente = pessoa
        o.save()
        return HttpResponseRedirect(reverse('sifilis:listar_por_pessoa', args=[pessoa_pk]))
    return render(request, 'sifilis/adicionar_exame.html', locals())

def adicionar_relacionamento(request, pessoa_pk):
    pessoa = PessoaFisica.objects.get(pk=pessoa_pk)
    form = RelacionamentoForm(data=request.POST or None)
    if form.is_valid():
        o = form.save(False)
        o.paciente = pessoa
        termo_de_busca = form.cleaned_data.get('cpf') or form.cleaned_data.get('cns')
        pessoa_relacionada = PessoaFisica.get_or_create_by_cpf_ou_cnes(termo_de_busca)
        if pessoa_relacionada:
            o.pessoa = pessoa_relacionada
            o.save()
            return HttpResponseRedirect(reverse('sifilis:listar_por_pessoa', args=[pessoa_pk]))
    return render(request, 'sifilis/adicionar_relacionamento.html', locals())

def adicionar_antecedente(request, pessoa_pk):
    pessoa = PessoaFisica.objects.get(pk=pessoa_pk)
    obj = Antecedente()
    obj.paciente = pessoa
    form = AntecedenteForm(data=request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse('sifilis:listar_por_pessoa', args=[pessoa_pk]))
    return render(request, 'sifilis/adicionar_antecedente.html', locals())


