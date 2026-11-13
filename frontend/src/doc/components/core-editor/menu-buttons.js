// Derived from frappe/suite@df7f341 (frontend/src/apps/writer)/components/core-editor/menu-buttons.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { __ } from '../../../kit/desk' // One: the desk's translations
import { h, defineAsyncComponent } from 'vue'
import ManageFont from '@/apps/writer/components/ManageFont.vue'
import DropdownMenuGroup from '@/apps/writer/components/core-editor/DropdownMenuGroup.vue'
import {
  Bold,
  Italic,
  Strike,
  InsertLink,
  FontColor,
  AlignLeft,
  AlignCenter,
  AlignRight,
  BulletList,
  OrderedList,
  Blockquote,
  InlineCode,
  InsertImage,
  InsertVideo,
  InsertIframe,
  InsertTable,
  Paragraph,
  H1,
  H2,
  H3,
  H4,
  Separator,
} from 'frappe-ui/editor'

import LucidePaintRoller from '~icons/lucide/paint-roller'
import LucideBrushCleaning from '~icons/lucide/brush-cleaning'
import LucideSettings from '~icons/lucide/settings'
import LucideForm from '~icons/lucide/sticky-note'
import LucideAlignVerticalSpacingAround from '~icons/lucide/align-vertical-space-around'
import LucideHeading from '~icons/lucide/heading'
import LucideAlignLeft from '~icons/lucide/align-left'
import LucideImagePlay from '~icons/lucide/image-plus'

const SpacingDialogAsync = defineAsyncComponent(() =>
  import('@/apps/writer/components/SpacingDialog.vue'),
)

const Underline = {
  label: __('Underline'),
  icon: 'lucide-underline',
  action: (e) => e.chain().focus().toggleUnderline().run(),
  isActive: (e) => e.isActive('underline'),
  isAvailable: (e) => !!e.can().toggleUnderline?.(),
}

const TaskListItem = {
  label: __('Task List'),
  icon: 'lucide-list-checks',
  action: (e) => e.chain().focus().toggleTaskList().run(),
  isActive: (e) => e.isActive('taskList'),
}

const TableOfContentsItem = {
  label: __('Table of Contents'),
  icon: 'lucide-table-of-contents',
  action: (e) => { e.commands.insertTableOfContentsNode(); return true },
  isAvailable: (e) => typeof e.commands.insertTableOfContentsNode === 'function',
}

const DedentList = {
  label: __('Dedent'),
  icon: 'lucide-indent-decrease',
  action: (e) => e.chain().focus().liftListItem('listItem').run(),
  isAvailable: (e) => e.can().liftListItem('listItem'),
}

const IndentList = {
  label: __('Indent'),
  icon: 'lucide-indent-increase',
  action: (e) => e.chain().focus().sinkListItem('listItem').run(),
  isAvailable: (e) => e.can().sinkListItem('listItem'),
}

// Dropdown group items
const headingItems = [Paragraph, H1, H2, H3, H4]
const alignItems = [AlignLeft, AlignCenter, AlignRight]

export function buildMenuButtons({ editor, settings, isPainting, openSettings, makePicture }) {
  return [
    // Heading type selector — dropdown group
    {
      label: __('Heading'),
      icon: LucideHeading,
      component: h(DropdownMenuGroup, {
        items: headingItems,
        defaultIcon: LucideHeading,
        defaultLabel: 'Heading',
      }),
      action: () => {},
    },
    Separator,
    Bold,
    Italic,
    Underline,
    Strike,
    InsertLink,
    FontColor,
    // Alignment — dropdown group
    {
      label: __('Align'),
      icon: LucideAlignLeft,
      component: h(DropdownMenuGroup, {
        items: alignItems,
        defaultIcon: LucideAlignLeft,
        defaultLabel: 'Align',
      }),
      action: () => {},
    },
    {
      label: __('Paint Styles'),
      icon: LucidePaintRoller,
      isActive: () => isPainting.value,
      action: (e) => {
        e.commands.focus()
        e.commands.storeStyles()
      },
    },
    {
      label: __('Clear formatting'),
      icon: LucideBrushCleaning,
      isActive: () => false,
      action: (e) => {
        e.commands.focus()
        e.commands.clearStyles()
        e.commands.cleanStyles()
      },
    },
    Separator,
    {
      label: 'FontOptions',
      component: h(ManageFont, {
        editor,
        font_size: +settings.font_size || 15,
        font_family: settings.font_family || 'inter',
      }),
      action: () => {},
    },
    Separator,
    BulletList,
    OrderedList,
    TaskListItem,
    Blockquote,
    InlineCode,
    Separator,
    InsertImage,
    // One: a picture OneAI makes, beside the one you upload (onedesk/one_doc/api.py, make_picture)
    ...(makePicture ? [{ label: __('Make a Picture with OneAI'), icon: LucideImagePlay, action: makePicture }] : []),
    InsertVideo,
    InsertIframe,
    Separator,
    InsertTable,
    TableOfContentsItem,
    Separator,
    {
      label: __('Page Break'),
      icon: LucideForm,
      action: (e) => e.commands.setPageBreak(),
    },
    {
      label: __('Custom Spacing'),
      icon: LucideAlignVerticalSpacingAround,
      component: h(SpacingDialogAsync, {
        settings,
        editor,
        icon: LucideAlignVerticalSpacingAround,
      }),
      action: () => {},
    },
    {
      icon: LucideSettings,
      label: __('Settings'),
      action: openSettings,
    },
    Separator,
    DedentList,
    IndentList,
  ]
}
