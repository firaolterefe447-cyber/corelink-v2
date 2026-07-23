(function($) {
    'use strict';

    $(document).ready(function() {
        // Apply enhanced field classes
        $('#id_title').closest('.form-row').addClass('title-field');
        $('#id_description').closest('.form-row').addClass('description-field');
        $('#id_profile').closest('.form-row').addClass('profile-field');
        $('#id_tags').closest('.form-row').addClass('tags-field');
        
        // Wrap category and subcategory in enhanced container
        var categoryField = $('#id_category');
        var subcategoryField = $('#id_subcategory');
        
        if (categoryField.length && subcategoryField.length) {
            // Create wrapper for category and subcategory
            var categoryRow = categoryField.closest('.form-row');
            var subcategoryRow = subcategoryField.closest('.form-row');
            
            // Wrap both fields in a container
            categoryRow.add(subcategoryRow).wrapAll('<div class="category-subcategory-wrapper"></div>');
            
            // Add enhanced field classes
            categoryField.parent().addClass('category-field');
            subcategoryField.parent().addClass('subcategory-field');
            
            // Add visual indicators
            categoryField.after('<span class="subcategory-indicator">📁</span>');
            subcategoryField.after('<span class="subcategory-indicator">📂</span>');
            
            // Function to load subcategories for a category
            function loadSubcategories(categoryId) {
                if (!categoryId) {
                    subcategoryField.empty().append('<option value="">Select category first</option>');
                    subcategoryField.prop('disabled', true);
                    subcategoryField.parent().css('opacity', '0.5');
                    return;
                }
                
                // Show loading state
                subcategoryField.empty().append('<option value="">Loading...</option>');
                subcategoryField.prop('disabled', true);
                subcategoryField.parent().css('opacity', '0.7');
                
                // Get the admin URL for subcategories API
                var url = '/api/subcategories/?category=' + categoryId;
                
                console.log('Loading subcategories from:', url);
                
                $.ajax({
                    url: url,
                    method: 'GET',
                    dataType: 'json',
                    success: function(data) {
                        console.log('Subcategories loaded:', data);
                        subcategoryField.empty().append('<option value="">Select subcategory (optional)</option>');
                        
                        if (data.subcategories && data.subcategories.length > 0) {
                            $.each(data.subcategories, function(index, sub) {
                                var option = $('<option></option>')
                                    .attr('value', sub.id)
                                    .text(sub.name);
                                subcategoryField.append(option);
                            });
                            subcategoryField.prop('disabled', false);
                            subcategoryField.parent().css('opacity', '1');
                            
                            // Add visual feedback
                            subcategoryField.parent().addClass('subcategory-active');
                            setTimeout(function() {
                                subcategoryField.parent().removeClass('subcategory-active');
                            }, 500);
                        } else {
                            subcategoryField.empty().append('<option value="">No subcategories available</option>');
                            subcategoryField.prop('disabled', true);
                            subcategoryField.parent().css('opacity', '0.5');
                        }
                    },
                    error: function(xhr, status, error) {
                        console.error('Error loading subcategories:', error, xhr.responseText);
                        subcategoryField.empty().append('<option value="">Error loading subcategories</option>');
                        subcategoryField.prop('disabled', true);
                        subcategoryField.parent().css('opacity', '0.5');
                    }
                });
            }
            
            // Handle both regular select and autocomplete fields
            function getCategoryValue() {
                // Check if it's an autocomplete field (hidden input)
                if (categoryField.is('input[type="hidden"]')) {
                    return categoryField.val();
                }
                // Regular select field
                return categoryField.val();
            }
            
            // Load subcategories when category changes
            categoryField.on('change', function() {
                var categoryId = getCategoryValue();
                console.log('Category changed to:', categoryId);
                loadSubcategories(categoryId);
                
                // Visual feedback on category change
                categoryField.parent().addClass('category-changed');
                setTimeout(function() {
                    categoryField.parent().removeClass('category-changed');
                }, 300);
            });
            
            // Also listen for autocomplete field changes via Django's event
            if (categoryField.hasClass('autocomplete')) {
                // Django autocomplete uses a different event system
                categoryField.on('autocompletechange', function() {
                    var categoryId = getCategoryValue();
                    console.log('Autocomplete category changed to:', categoryId);
                    loadSubcategories(categoryId);
                });
            }
            
            // Use MutationObserver to detect changes in autocomplete fields
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'value') {
                        var categoryId = getCategoryValue();
                        console.log('Category value changed via observer:', categoryId);
                        loadSubcategories(categoryId);
                    }
                });
            });
            
            observer.observe(categoryField[0], { attributes: true, attributeFilter: ['value'] });
            
            // Initial load if category is already selected
            var initialCategoryId = getCategoryValue();
            console.log('Initial category ID:', initialCategoryId);
            if (initialCategoryId) {
                loadSubcategories(initialCategoryId);
            } else {
                subcategoryField.empty().append('<option value="">Select category first</option>');
                subcategoryField.prop('disabled', true);
                subcategoryField.parent().css('opacity', '0.5');
            }
        }
        
        // Enhanced form field interactions
        $('.form-row input, .form-row textarea, .form-row select').on('focus', function() {
            $(this).closest('.form-row').addClass('field-focused');
        }).on('blur', function() {
            $(this).closest('.form-row').removeClass('field-focused');
        });
        
        // Smooth scroll to first error
        if ($('.errorlist').length > 0) {
            $('html, body').animate({
                scrollTop: $('.errorlist').first().offset().top - 100
            }, 500);
        }
        
        // Add character counter for description
        var descriptionField = $('#id_description');
        if (descriptionField.length) {
            var charCounter = $('<div class="char-counter">0 characters</div>');
            descriptionField.after(charCounter);
            
            function updateCharCounter() {
                var length = descriptionField.val().length;
                charCounter.text(length + ' characters');
                
                if (length > 500) {
                    charCounter.css('color', '#e53e3e');
                } else if (length > 300) {
                    charCounter.css('color', '#ed8936');
                } else {
                    charCounter.css('color', '#718096');
                }
            }
            
            descriptionField.on('input', updateCharCounter);
            updateCharCounter();
        }
        
        // Add word counter for title
        var titleField = $('#id_title');
        if (titleField.length) {
            var wordCounter = $('<div class="word-counter">0 words</div>');
            titleField.after(wordCounter);
            
            function updateWordCounter() {
                var text = titleField.val().trim();
                var words = text ? text.split(/\s+/).length : 0;
                wordCounter.text(words + ' words');
                
                if (words > 15) {
                    wordCounter.css('color', '#e53e3e');
                } else if (words > 10) {
                    wordCounter.css('color', '#ed8936');
                } else {
                    wordCounter.css('color', '#718096');
                }
            }
            
            titleField.on('input', updateWordCounter);
            updateWordCounter();
        }
    });

})(django.jQuery);
