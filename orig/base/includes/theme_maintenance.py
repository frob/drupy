#!/usr/bin/env python
# $Id: theme.maintenance.inc,v 1.14 2008/06/25 09:12:24 dries Exp $

"""
  Theming for maintenance pages.
  Sets up the theming system for site installs, updates and when the site is
  in off-line mode. It also applies when the database is unavailable.

  @package includes
  @see <a href='http://drupy.net'>Drupy Homepage</a>
  @see <a href='http://drupal.org'>Drupal Homepage</a>
  @note Drupy is a port of the Drupal project.
  @note This file was ported from Drupal's includes/theme.maintenance.inc
  @author Brendon Crawford
  @copyright 2008 Brendon Crawford
  @contact message144 at users dot sourceforge dot net
  @created 2008-01-10
  @version 0.1
  @note License:

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to:
    
    The Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1301,
    USA
"""

__version__ = "$Revision: 1 $"

#
# Minnelli is always used for the initial install and update operations. In
# other cases, "settings.php" must have a "maintenance_theme" key set for the
# conf variable in order to change the maintenance theme.
#


#
# Imports
#
from lib.drupy import DrupyPHP as php
import path as lib_path
import theme as lib_theme
import common as lib_common
import unicode as lib_unicode
import file as lib_file
import plugin as lib_plugin
import database as lib_database


def _drupal_maintenance_theme():
  # If theme is already set, assume the others are set too, and do nothing.
  if (lib_appglobals.theme is not None):
    return
  lib_unicode.check()
  # Install and update pages are 
  # treated differently to prevent theming overrides.
  if (php.defined('MAINTENANCE_MODE') and \
      (MAINTENANCE_MODE == 'install' or MAINTENANCE_MODE == 'update')):
    lib_appglobals.theme = 'minnelli'
  else:
    # Load plugin basics (needed for hook invokes).
    plugin_list_ = { 'system' : {}, 'filter' : {} }
    plugin_list_['system']['filename'] = 'plugins/system/system.py'
    plugin_list_['filter']['filename'] = 'plugins/filter/filter.py'
    lib_plugin.list(True, False, False, plugin_list_)
    drupal_load('plugin', 'system')
    drupal_load('plugin', 'filter')
    lib_appglobals.theme = variable_get('maintenance_theme', 'minnelli')
  themes = list_themes()
  # Store the identifier for retrieving theme settings with.
  lib_appglobals.theme_key = lib_appglobals.theme
  # Find all our ancestor themes and put them in an array.
  base_theme = []
  ancestor = lib_appglobals.theme
  while (ancestor and php.isset(themes[ancestor], base_theme)):
    new_base_theme = themes[themes[ancestor].base_theme]
    base_theme.append(new_base_theme)
    ancestor = themes[ancestor].base_theme
  _init_theme(themes[lib_appglobals.theme], php.array_reverse(base_theme), \
    '_theme_load_offline_registry')
  # These are usually added from system_init() -except maintenance.css.
  # When the database is inactive it's not called so we add it here.
  drupal_add_css(drupal_get_path('plugin', 'system') + \
    '/defaults.css', 'plugin')
  drupal_add_css(drupal_get_path('plugin', 'system') + \
    '/system.css', 'plugin')
  drupal_add_css(drupal_get_path('plugin', 'system') + \
    '/system-menus.css', 'plugin')
  drupal_add_css(drupal_get_path('plugin', 'system') + \
    '/maintenance.css', 'plugin')
#
# This builds the registry when the site needs to bypass any database calls.
#
def _load_offline_registry(this_theme, \
                                 base_theme = None, theme_engine = None):
  registry = _theme_build_registry(this_theme, base_theme, theme_engine)
  _theme_set_registry(registry)



def task_list(items_, active = None):
  """
   Return a themed list of maintenance tasks to perform.
  
   @ingroup themeable
  """
  done = ((active == None) or (php.isset(items, active)))
  output = '<ol class="task-list">'
  for k,item in items_.items():
    if (active == k):
      class_ = 'active'
      done = False
    else:
      class_ = ('done' if done else '')
    output += '<li class="' + class_ + '">' + item + '</li>'
  output += '</ol>'
  return output



def install_page(content):
  """
   Generate a themed installation page.
  
   Note: this function is not themeable.
  
   @param content
     The page content to show.
  """
  drupal_set_header('Content-Type: text/html; charset=utf-8')
  # Assign content.
  variables['content'] = content
  # Delay setting the message variable so it can be processed below.
  variables['show_messages'] = False
  # The maintenance preprocess function is recycled here.
  template_preprocess_maintenance_page(variables)
  # Special handling of error messages
  messages = drupal_set_message()
  if (php.isset(messages, 'error')):
    title = (st('The following errors must be resolved before you can ' + \
      'continue the installation process') if \
      (php.count(messages['error']) > 1) else \
      st('The following error must be resolved before you can ' + \
      'continue the installation process'))
    variables['messages'] += '<h3>' + title + ':</h3>'
    variables['messages'] += theme('status_messages', 'error')
    variables['content'] += '<p>' + st('Please check the error ' + \
      'messages and <a href="not url">try again</a>.', \
      {'not url' : request_uri()}) + '</p>'
  # Special handling of warning messages
  if (php.isset(messages, 'warning')):
    title = (st('The following installation warnings should be ' + \
      'carefully reviewed') if \
      (php.count(messages['warning']) > 1) else \
      st('The following installation warning should be carefully reviewed'))
    variables['messages'] += '<h4>' + title + ':</h4>'
    variables['messages'] += theme('status_messages', 'warning')
  # Special handling of status messages
  if (php.isset(messages, 'status')):
    title = (st('The following installation warnings should be ' + \
      'carefully reviewed, but in most cases may be safely ignored') if \
      (php.count(messages['status']) > 1) else st('The following ' + \
      'installation warning should be carefully reviewed, but in ' + \
      'most cases may be safely ignored'))
    variables['messages'] += '<h4>' + title + ':</h4>'
    variables['messages'] += theme('status_messages', 'status')
  # This was called as a theme hook (not template), so we need to
  # fix path_to_theme() for the template, to point at the actual
  # theme rather than system plugin as owner of the hook.
  lib_appglobals.theme_path = 'themes/garland'
  return theme_render_template('themes/garland/maintenance-page.tpl.py', \
    variables)



def update_page(content, show_messages = True):
  """
   Generate a themed update page.
  
   Note: this function is not themeable.
  
   @param content
     The page content to show.
   @param show_messages
     Whether to output status and error messages.
     False can be useful to postpone the messages to a subsequent page.
  """
  # Set required headers.
  drupal_set_header('Content-Type: text/html; charset=utf-8')
  # Assign content and show message flag.
  variables['content'] = content
  variables['show_messages'] = show_messages
  # The maintenance preprocess function is recycled here.
  template_preprocess_maintenance_page(variables)
  # Special handling of warning messages.
  messages = drupal_set_message()
  if (php.isset(messages['warning'])):
    title = ('The following update warnings should be carefully ' + \
      'reviewed before continuing' if \
      (php.count(messages['warning']) > 1) else \
        'The following update warning should be carefully ' + \
        'reviewed before continuing')
    variables['messages'] += '<h4>' + title + ':</h4>'
    variables['messages'] += theme('status_messages', 'warning')
  # This was called as a theme hook (not template), so we need to
  # fix path_to_theme() for the template, to point at the actual
  # theme rather than system plugin as owner of the hook.
  lib_appglobals.theme_path = 'themes/garland'
  return theme_render_template('themes/garland/maintenance-page.tpl.php', \
    variables)



def template_preprocess_maintenance_page(variables):
  """
   The variables generated here is a mirror of template_preprocess_page().
   This preprocessor will run it's course when theme_maintenance_page() is
   invoked. It is also used in theme_install_page() and theme_update_page() to
   keep all the variables consistent.
  
   An alternate template file of "maintenance-page-offline.tpl.php" can be
   used when the database is offline to hide errors and completely replace the
   content.
  
   The variables array contains the following arguments:
   - content
   - show_blocks
  
   @see maintenance-page.tpl.php
  """
  php.Reference.check(variables)
  # Add favicon
  if (theme_get_setting('toggle_favicon')):
    drupal_set_html_head('<link rel="shortcut icon" href="' + \
      check_url(theme_get_setting('favicon')) + '" type="image/x-icon" />');
  # Retrieve the theme data to list all available regions.
  theme_data = _system_theme_data()
  regions = theme_data[lib_appglobals.theme].info['regions']
  # Get all region content set with drupal_set_content().
  for region in php.array_keys(regions):
    # Assign region to a region variable.
    region_content = drupal_get_content(region)
    if php.isset(variables, region):
      variables[region] += region_content
    else:
      variables[region] = region_content
  # Setup layout variable.
  variables['layout'] = 'none'
  if (not php.empty(variables['left'])):
    variables['layout'] = 'left'
  if (not php.empty(variables['right'])):
    variables['layout'] = ('both' if \
      (variables['layout'] == 'left') else 'right')
  # Construct page title
  if (drupal_get_title()):
    head_title = [strip_tags(drupal_get_title()), \
      variable_get('site_name', 'Drupal')];
  else:
    head_title = [variable_get('site_name', 'Drupal')]
    if (variable_get('site_slogan', '')):
      head_title.append( variable_get('site_slogan', '') )
  variables['head_title']        = php.implode(' | ', head_title)
  variables['base_path']         = base_path()
  variables['front_page']        = url()
  variables['breadcrumb']        = ''
  variables['feed_icons']        = ''
  variables['footer_message']    = \
    filter_xss_admin(variable_get('site_footer', FALSE))
  variables['head']              = drupal_get_html_head()
  variables['help']              = ''
  variables['language']          = lib_appglobals.language
  variables['language'].dir      = \
    ('rtl' if lib_appglobals.language.direction else 'ltr')
  variables['logo']              = theme_get_setting('logo');
  variables['messages']          = (theme('status_messages') if \
    variables['show_messages'] else '')
  variables['mission']           = '';
  variables['main_menu']         = [];
  variables['secondary_menu']    = [];
  variables['search_box']        = '';
  variables['site_name']         = \
    (variable_get('site_name', 'Drupal') if \
    theme_get_setting('toggle_name')  else '')
  variables['site_slogan']       = (variable_get('site_slogan', '') if \
    theme_get_setting('toggle_slogan') else '')
  variables['css']               = drupal_add_css()
  variables['styles']            = drupal_get_css()
  variables['scripts']           = drupal_get_js()
  variables['tabs']              = ''
  variables['title']             = drupal_get_title();
  variables['closure']           = ''
  # Compile a list of classes that are going to be applied to the body element.
  body_classes = []
  body_classes.append( 'in-maintenance' )
  if (php.isset(variables, 'db_is_active') and \
      not variables['db_is_active']):
    body_classes.append( 'db-offline' )
  if (variables['layout'] == 'both'):
    body_classes.append( 'two-sidebars' )
  elif (variables['layout'] == 'none'):
    body_classes.append( 'no-sidebars' )
  else:
    body_classes.append( 'one-sidebar sidebar-'  + variables['layout'] )
  variables['body_classes'] = php.implode(' ', body_classes)
  # Dead databases will show error messages so supplying this template will
  # allow themers to override the page and the content completely.
  if (php.isset(variables, 'db_is_active') and \
      not variables['db_is_active']):
    variables['template_file'] = 'maintenance-page-offline';



