$(document).ready(function () {
  $('input[type="checkbox"]').on('click', function () {
    const $checkbox = $(this);
    const $form = $('#connector-form-' + this.id.split('-')[2]);
    if ($checkbox.is(':checked')) {
      $form.removeClass('hidden').addClass('visible');
    } else {
      $form.removeClass('visible').addClass('hidden');
    }
  });
});