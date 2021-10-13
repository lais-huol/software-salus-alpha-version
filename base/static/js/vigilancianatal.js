function notificationAsHTML(obj) {
    return '<a href="javascript:void(0);" class="dropdown-item notify-item active">\n' +
        '<div class="notify-icon bg-soft-primary text-primary">\n' +
        '<i class="mdi mdi-comment-account-outline"></i>\n' +
        '</div>\n' +
        '<p class="notify-details">'+ obj.verb +
        '<small class="text-muted">'+ obj.timestamp + '</small>\n' +
        '</p>\n' +
        '</a>'
}

function getNotifications() {
    $(".slimscroll").empty();
    $.get( "/inbox/notifications/api/unread_list/", function( unread_list_data ) {
        let item;
        for (let i = 0; i < unread_list_data["unread_list"].length; i++) {
            item = unread_list_data["unread_list"][i];
            $(".slimscroll").append(notificationAsHTML(item));
        }
    });
}

$(document).ready(function(){
    function getAlertsCount(){
        let notifications_badge = $(".notification-list .dropdown-toggle .badge");
        $.get( "/inbox/notifications/api/unread_count/", function( unread_count_data ) {
            let current_count = parseInt(notifications_badge.html());
            let new_count = unread_count_data['unread_count'];
            if (current_count !== new_count) {
                notifications_badge.html(unread_count_data['unread_count'])
                if (new_count !== 0) {
                    notifications_badge.show()
                    getNotifications();
                } else {
                    notifications_badge.hide();
                    $(".slimscroll").empty();
                }
            }
        });
        setTimeout(getAlertsCount, 10000);
    }
    getAlertsCount();
})

function reloadTriggers() {
    $(document).on('click', '.notificacao-detalhe-modal-trigger', function () {
        notificacaoDetalheModal($(this));
    });
    $(document).on('click', '.obito-detalhe-modal-trigger', function () {
        obitoDetalheModal($(this));
    });
    $(document).on('click', ".monitoramento-detalhe-modal-trigger", function () {
        monitoramentoDetalheModal($(this));
    });
    $(document).on('click', ".notificacao-alterar-gal", function () {
        notificacaoGalModal($(this));
    });
    $(document).on('click', ".mostrar-modal", function () {
        detalheModal($(this));
    });

    $('#iframeModal').on('show.bs.modal', function (event) {
        iframer = $(this).find('iframe')
        iframer.attr('src', iframer.attr('data-src'))
    });
}

function notificacaoDetalheModal(trigger) {
    url = "/notificacoes/" + trigger.data("notificacao") + "/"
    let modal = $("#modal-iframe");
    modal.modal('show');
    $("#iframe-comp").attr('src', url)
    // modal.find('iframe').attr('src',)
}
function detalheModal(trigger) {
    url = trigger.data("target")
    let modal = $("#modal-iframe");
    modal.modal('show');
    $("#iframe-comp").attr('src', url)
}

function fecharModalIframe(){
    $('#modal-iframe').modal('hide');
}

function notificacaoGalModal(trigger) {
    let modal = $("#baseModal");
    $.get("/notificacoes/" + trigger.data("notificacao") + "/alterar_gal/", function (data) {
        modal.find('.modal-content').html(data);
        $('#baseModal').modal('show');
    });
}

function monitoramentoDetalheModal(trigger) {
    let modal = $("#baseModal");
    $.get("/notificacoes/monitoramentos/" + trigger.data("monitoramento") + "/", function (data) {
        modal.find('.modal-content').html(data);
        $('#baseModal').modal('show');
    });
}

function obitoDetalheModal(trigger) {
  url = "/notificacoes/obitos/" + trigger.data("obito") + "/"
    let modal = $("#modal-iframe");
    modal.modal('show');
    $("#iframe-comp").attr('src', url)
    // modal.find('iframe').attr('src',)
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}