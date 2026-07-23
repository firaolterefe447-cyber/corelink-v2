(function($) {
    'use strict';

    $(document).ready(function() {
        // Dynamic subcategory filtering based on category selection
        var categoryField = $('#id_category');
        var subcategoryField = $('#id_subcategory');
        
        if (categoryField.length && subcategoryField.length) {
            
            // Function to load subcategories for a category
            function loadSubcategories(categoryId) {
                if (!categoryId) {
                    subcategoryField.empty().append('<option value="">---------</option>');
                    subcategoryField.prop('disabled', true);
                    return;
                }
                
                // Get the admin URL for subcategories API
                var url = '/api/subcategories/?category=' + categoryId;
                
                $.ajax({
                    url: url,
                    method: 'GET',
                    dataType: 'json',
                    success: function(data) {
                        subcategoryField.empty().append('<option value="">---------</option>');
                        
                        if (data.subcategories && data.subcategories.length > 0) {
                            $.each(data.subcategories, function(index, sub) {
                                var option = $('<option></option>')
                                    .attr('value', sub.id)
                                    .text(sub.name);
                                subcategoryField.append(option);
                            });
                            subcategoryField.prop('disabled', false);
                        } else {
                            subcategoryField.prop('disabled', true);
                        }
                    },
                    error: function(xhr, status, error) {
                        console.error('Error loading subcategories:', error);
                        subcategoryField.empty().append('<option value="">Error loading subcategories</option>');
                        subcategoryField.prop('disabled', true);
                    }
                });
            }
            
            // Load subcategories when category changes
            categoryField.on('change', function() {
                var categoryId = $(this).val();
                loadSubcategories(categoryId);
            });
            
            // Initial load if category is already selected
            if (categoryField.val()) {
                loadSubcategories(categoryField.val());
            } else {
                subcategoryField.prop('disabled', true);
            }
        }
    });

})(django.jQuery);
