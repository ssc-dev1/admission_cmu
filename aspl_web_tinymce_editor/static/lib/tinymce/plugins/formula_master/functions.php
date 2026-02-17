<?php
/**
 * Functions.
 *
 * @package TinyMCE Formula plugin
 */

add_action( 'functions/Inputs.php|tinymce_before_init', 'TinyMCEFormulaPlugin' );

function TinyMCEFormulaPlugin()
{
	$site_url = 'http';

	if ( isset( $_SERVER['HTTPS'] )
		&& $_SERVER['HTTPS'] == 'on' )
	{
		$site_url .= 's';
	}

	$site_url .= '://';

	if ( $_SERVER['SERVER_PORT'] != '80'
		&& $_SERVER['SERVER_PORT'] != '443' )
	{
		$site_url .= $_SERVER['SERVER_NAME'] . ':' . $_SERVER['SERVER_PORT'] . dirname( $_SERVER['PHP_SELF'] );
	}
	else
	{
		$site_url .= $_SERVER['SERVER_NAME'] . dirname( $_SERVER['PHP_SELF'] );
	}

	$plugin_url = $site_url . '/plugins/TinyMCE_Formula/tinymce-formula/';
	$plugin_js_url = $plugin_url . 'plugin.min.js';
	?>
	<script>
		tinymceSettings.plugins += ' formula';
		tinymceSettings.toolbar += ' formula';
		tinymceSettings.external_plugins.formula = <?php echo json_encode( $plugin_js_url ); ?>;
	</script>
	<?php
}
