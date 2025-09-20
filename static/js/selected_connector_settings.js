$(document).ready(function () {

  /***
   * Show/hide connector settings forms based on checkbox state
   *
   */
  $('input[type="checkbox"]').on('click', function () {
    const $checkbox = $(this);
    const $form = $('#connector-form-' + this.id.split('-')[2]);
    if ($checkbox.is(':checked')) {
      $form.removeClass('hidden').addClass('visible');
    } else {
      $form.removeClass('visible').addClass('hidden');
    }
  });

  /***
   * Unmask/mask password fields
   *
   */
  $('.toggle-eye').each(function () {
    $(this).on('click', function () {
      var $input = $(this).parent().find('.password-field');
      if ($input.val() === '********') {
        $input.removeAttr('readonly');
        $input.val($input.attr('data-actual'));
        $(this).html('<i class="fa fa-eye"></i>');
      } else {
        $input.attr('readonly', true);
        $input.val('********');
        $(this).html('<i class="fa fa-eye-slash"></i>');
      }
    });
  });

});
