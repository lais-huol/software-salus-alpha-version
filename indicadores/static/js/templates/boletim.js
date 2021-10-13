/**
 * @license Copyright (c) 2003-2020, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see LICENSE.md or https://ckeditor.com/legal/ckeditor-oss-license
 */

// Register a templates definition set named "default".
CKEDITOR.addTemplates('default', {
    // The name of sub folder which hold the shortcut preview images of the
    // templates.
    imagesPath: CKEDITOR.getUrl(CKEDITOR.plugins.getPath('templates') + 'templates/images/'),

    // The templates definitions.
    templates: [
        {
            title: 'Duas colunas 50%/50%',
            image: 'template2.gif',
            description: 'Modelo para apresentar conteúdo em duas colunas.',
            html: '<div class="row">' +
                // Use src=" " so image is not filtered out by the editor as incorrect (src is required).
                '<div class="col-md-6"> Conteúdo a esquerda </div>' +
                '<div class="col-md-6"> Conteúdo a direita </div>' +
                '</div>'
        },
        {
            title: 'Duas colunas 70%/30%',
            image: 'template2.gif',
            description: 'Modelo para apresentar conteúdo em duas colunas.',
            html: '<div class="row">' +
                // Use src=" " so image is not filtered out by the editor as incorrect (src is required).
                '<div class="col-md-9"> Conteúdo a esquerda </div>' +
                '<div class="col-md-3"> Conteúdo a direita </div>' +
                '</div>'
        },
        {
            title: 'Duas colunas 30%/70%',
            image: 'template2.gif',
            description: 'Modelo para apresentar conteúdo em duas colunas.',
            html: '<div class="row">' +
                // Use src=" " so image is not filtered out by the editor as incorrect (src is required).
                '<div class="col-md-3"> Conteúdo a esquerda </div>' +
                '<div class="col-md-9"> Conteúdo a direita </div>' +
                '</div>'
        }
    ]
});