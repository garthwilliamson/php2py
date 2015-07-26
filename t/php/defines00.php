<?php

define('URL_PUBLIC_FOLDER', 'public');
define('URL_DOMAIN', $_SERVER['HTTP_HOST']);
define('URL_SUB_FOLDER', str_replace(URL_PUBLIC_FOLDER, '', dirname($_SERVER['SCRIPT_NAME'])));

echo(URL_DOMAIN . "\n");
echo( $_SERVER['SCRIPT_NAME'] . "\n");
echo( dirname($_SERVER['SCRIPT_NAME']) . "\n");
echo(URL_SUB_FOLDER . "\n");
