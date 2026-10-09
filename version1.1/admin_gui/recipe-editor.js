/* Shared Admin drink/recipe editor used by standalone and all-in-one pages. */
(function (global) {
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;',
  })[character]);

  function invalid(message) {
    const error = new Error(message);
    error.code = 'invalid_recipe';
    throw error;
  }

  function positiveInteger(value, field) {
    const number = Number(value);
    if (!Number.isInteger(number) || number <= 0) invalid(`${field} phải là số nguyên dương.`);
    return number;
  }

  function buildDocument(input) {
    const name = String(input.name || '').trim();
    if (!name) invalid('Tên món không được để trống.');
    const price = Number(input.price);
    if (!Number.isFinite(price) || price < 0) invalid('Giá phải là số không âm.');
    /* Unticking every box is now something a person can do, so it needs an
       answer of its own. Left to positiveInteger() it came back as "Danh
       mục phải là số nguyên dương" -- true, and no help at all to somebody
       who simply has not ticked anything yet. */
    const rawCategoryIds = Array.isArray(input.categoryIds)
      ? input.categoryIds
      : [input.categoryId];
    if (!rawCategoryIds.filter(value => value !== '' && value != null).length) {
      invalid('Phải chọn ít nhất một danh mục cho món này.');
    }
    const categoryIds = rawCategoryIds.map(value => positiveInteger(value, 'Danh mục'));
    if (!Array.isArray(input.steps) || input.steps.length === 0) {
      invalid('Công thức phải có ít nhất một bước.');
    }

    const steps = input.steps.map((step, stepIndex) => {
      // A step is EITHER a pour or an action, never both. An action pours
      // nothing, so the ingredient rules below simply do not apply to it.
      if (step.action) {
        if (!String(step.action.media_src || '').trim()) {
          invalid(`Bước ${stepIndex + 1}: chưa chọn phim hướng dẫn.`);
        }
        if (!String(step.action.title_vi || '').trim()) {
          invalid(`Bước ${stepIndex + 1}: bước thao tác phải có tiêu đề.`);
        }
        return { step_no:stepIndex + 1, ingredients:[], action:step.action };
      }

      if (!Array.isArray(step.ingredients) || step.ingredients.length === 0) {
        invalid(`Bước ${stepIndex + 1} phải có ít nhất một nguyên liệu.`);
      }
      const seen = new Set();
      const ingredients = step.ingredients.map((ingredient, ingredientIndex) => {
        const ingredientId = positiveInteger(
          ingredient.ingredientId,
          `Nguyên liệu ${ingredientIndex + 1} của bước ${stepIndex + 1}`,
        );
        if (seen.has(ingredientId)) {
          invalid(`Bước ${stepIndex + 1} đang có nguyên liệu trùng nhau.`);
        }
        seen.add(ingredientId);
        const targetGram = Number(ingredient.targetGram);
        if (!Number.isFinite(targetGram) || targetGram <= 0) {
          invalid(`Số gram ở bước ${stepIndex + 1} phải lớn hơn 0.`);
        }
        return { ingredient_id:ingredientId, target_gram:targetGram };
      });
      return { step_no:stepIndex + 1, ingredients };
    });

    const drink = {
      name,
      image:String(input.image || '').trim() || null,
      price,
      // "" is the "— Chưa đặt —" option: sent as null so the column is
      // cleared rather than written with an id of 0.
      glass_id:input.glassId === '' || input.glassId == null
        ? null : Number(input.glassId),
      // Same "" -> null rule as the glass: "— Chưa đặt —" clears the
      // column rather than writing an id of 0.
      drink_type_id:input.drinkTypeId === '' || input.drinkTypeId == null
        ? null : Number(input.drinkTypeId),
      garnish:String(input.garnish || '').trim() || null,
      // Belongs to the drink_type row, not to this drink. Sent as '' when
      // cleared and omitted entirely when no type is chosen, so the server
      // can tell "empty it" from "the form never offered it".
      drink_type_detail:input.drinkTypeId ? String(input.drinkTypeDetail ?? '') : undefined,
      available:Boolean(input.available),
      category_ids:[...new Set(categoryIds)],
    };
    if (input.drinkId != null) {
      drink.drink_id = positiveInteger(input.drinkId, 'Drink ID');
    }
    return { drink, steps };
  }

  /* What the shared-description box says under itself. Named rather than
     inlined because the change handler rewrites it when the picker moves
     to a different build method. */
  function detailHint(type) {
    if (!type) {
      return 'Chọn kiểu pha ở trên để sửa mô tả của kiểu đó.';
    }
    const others = Number(type.drink_count || 0) - 1;
    if (others > 0) {
      return `Mô tả này thuộc về kiểu <b>${escapeHtml(type.type_name)}</b>` +
             ` — sửa ở đây sẽ đổi cho cả ${others} món khác đang dùng kiểu này.`;
    }
    return `Mô tả này thuộc về kiểu <b>${escapeHtml(type.type_name)}</b>.` +
           ' Hiện chỉ món này đang dùng kiểu đó.';
  }

  function ingredientOptions(ingredients, selectedId) {
    if (!ingredients.length) return '<option value="">Không có nguyên liệu đã gắn pump</option>';
    return ingredients.map(ingredient => {
      const id = Number(ingredient.ingredient_id);
      return `<option value="${id}" ${id === Number(selectedId) ? 'selected' : ''}>` +
        `${escapeHtml(ingredient.ingredient_name)}</option>`;
    }).join('');
  }

  function ingredientRow(ingredients, ingredient = {}) {
    return `<div class="recipe-ingredient" data-recipe-ingredient>
      <select data-ingredient-id>${ingredientOptions(ingredients, ingredient.ingredient_id)}</select>
      <input data-target-gram type="number" min="0.01" step="0.01" value="${escapeHtml(ingredient.target_gram ?? 1)}" aria-label="Số gram">
      <button type="button" class="iconbtn del" data-remove-ingredient title="Bỏ nguyên liệu">&times;</button>
    </div>`;
  }

  /* The current clip, drawn the way the guide screen will draw it: a
     <video> for the formats that need one, an <img> for a GIF. Same tag
     choice as bartender_gui/js/guide.js, so what the admin sees moving
     here is what the bartender sees moving there. */
  function mediaTile(src) {
    if (!src) return '<span class="mediapick-empty">Chưa có</span>';
    const url = '../recipe/media/' + encodeURIComponent(src);
    return /\.(mp4|webm)$/i.test(src)
      ? `<video src="${url}" autoplay loop muted playsinline></video>`
      : `<img src="${url}" alt="">`;
  }

  /* The grab bar, at the head of every step. A real <button> rather than a
     decorated <span>: focused, the arrow keys move the step, which is the
     only way to reorder one without a pointer. */
  function dragHandle() {
    return `<button type="button" class="step-drag" data-step-drag
      title="Kéo để đổi thứ tự bước (hoặc bấm vào rồi dùng phím \u2191 \u2193)"
      aria-label="Đổi thứ tự bước">
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <circle cx="9" cy="6" r="1.55"/><circle cx="15" cy="6" r="1.55"/>
        <circle cx="9" cy="12" r="1.55"/><circle cx="15" cy="12" r="1.55"/>
        <circle cx="9" cy="18" r="1.55"/><circle cx="15" cy="18" r="1.55"/>
      </svg>
    </button>`;
  }

  /* The step's name, which is also the lid. A long recipe is mostly cards
     nobody is editing at that moment, so the whole head is the hit target
     rather than a chevron alone -- everything but the grab bar and "Bỏ
     bước" opens and shuts the card.

     The summary beside it is what a shut card has left to say: the pour it
     makes, or the title of the action. Filled in at the moment of closing,
     from the fields as they stand, so it can never describe a value that
     has since been typed over. */
  function stepTitle(index, tag = '') {
    return `<button type="button" class="step-title" data-step-toggle aria-expanded="true"
        title="Bấm để thu gọn hoặc mở lại bước này">
      <svg class="chev" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="m9 5.5 7 6.5-7 6.5"/>
      </svg>
      <strong>Bước <span data-step-number>${index + 1}</span></strong>${tag}
      <span class="step-summary" data-step-summary></span>
    </button>`;
  }

  /* An action step: the bartender does something the machine cannot, with
     a clip looping on the guide screen to show how. Rendered as its own
     card rather than a mode of the pour card -- the two share nothing but
     a step number, and a toggle between them would have to decide what to
     do with the fields the other kind does not have. */
  function actionStep(step = {}, index = 0) {
    const action = step.action || {};
    const media = String(action.media_src || '');
    const returns = action.cup_returns !== false;
    return `<div class="recipe-step" data-recipe-step data-step-kind="action">
      <div class="recipe-step-head">
        ${dragHandle()}
        ${stepTitle(index, '<span class="step-kind-tag">thao tác</span>')}
        <button type="button" class="btn ghost compact" data-remove-step>Bỏ bước</button>
      </div>

      <div data-step-body>
      <div class="action-fields">
        <div class="mfield">
          <label>Phim hướng dẫn</label>
          <div class="mediapick">
            <div class="mediapick-now" data-media-preview>${mediaTile(media)}</div>
            <div class="mediapick-side">
              <div class="mediapick-name" data-media-name>${
                media ? escapeHtml(media) : 'Chưa chọn phim'}</div>
              <div class="mediapick-btns">
                <label class="btn ghost compact">
                  Tải phim lên
                  <input type="file" accept="video/mp4,video/webm,image/gif"
                         data-media-file hidden>
                </label>
                <button type="button" class="btn ghost compact" data-media-browse>
                  Chọn phim có sẵn
                </button>
                <button type="button" class="btn ghost compact" data-media-clear>
                  Bỏ phim
                </button>
              </div>
            </div>
          </div>
          <input type="hidden" data-media-src value="${escapeHtml(media)}">
          <div class="imglib" data-media-library hidden></div>
          <div class="mhint">MP4, WEBM hoặc GIF. Quay ngang, chủ thể vào giữa —
            màn hình cắt theo khung 4:3.</div>
        </div>

        <div class="mfield">
          <label>Tiêu đề (VI)</label>
          <input data-action-field="title_vi" maxlength="120"
                 value="${escapeHtml(action.title_vi ?? '')}"
                 placeholder="Lắc ly 10 giây">
        </div>
        <div class="mfield">
          <label>Tiêu đề (EN)</label>
          <input data-action-field="title_en" maxlength="120"
                 value="${escapeHtml(action.title_en ?? '')}"
                 placeholder="Shake for 10 seconds">
        </div>

        <div class="mfield">
          <label>Mô tả (VI)</label>
          <textarea data-action-field="detail_vi" rows="2" maxlength="400"
            placeholder="Nhấc ly khỏi bàn cân, đổ vào shaker cùng đá…">${
              escapeHtml(action.detail_vi ?? '')}</textarea>
        </div>
        <div class="mfield">
          <label>Mô tả (EN)</label>
          <textarea data-action-field="detail_en" rows="2" maxlength="400"
            placeholder="Lift the glass off the scale…">${
              escapeHtml(action.detail_en ?? '')}</textarea>
        </div>

        <div class="mfield">
          <label>Chữ trên nút (VI)</label>
          <input data-action-field="confirm_vi" maxlength="40"
                 value="${escapeHtml(action.confirm_vi ?? '')}" placeholder="ĐÃ LẮC XONG">
        </div>
        <div class="mfield">
          <label>Chữ trên nút (EN)</label>
          <input data-action-field="confirm_en" maxlength="40"
                 value="${escapeHtml(action.confirm_en ?? '')}" placeholder="SHAKEN">
        </div>
      </div>

      <label class="action-returns">
        <input type="checkbox" data-cup-returns ${returns ? 'checked' : ''}>
        <span><strong>Ly rời khỏi bàn cân</strong>
          <em>Máy sẽ chờ ly quay lại rồi mới bơm tiếp. Bỏ chọn nếu đây là
          bước cuối, hoặc ly vẫn đứng yên trên cân.</em></span>
      </label>
      </div>
    </div>`;
  }

  function recipeStep(ingredients, step = {}, index = 0) {
    const rows = Array.isArray(step.ingredients) && step.ingredients.length
      ? step.ingredients
      : [{ ingredient_id:ingredients[0]?.ingredient_id, target_gram:1 }];
    return `<div class="recipe-step" data-recipe-step data-step-kind="pump">
      <div class="recipe-step-head">
        ${dragHandle()}
        ${stepTitle(index)}
        <button type="button" class="btn ghost compact" data-remove-step>Bỏ bước</button>
      </div>
      <div data-step-body>
        <div data-ingredient-list>${rows.map(row => ingredientRow(ingredients, row)).join('')}</div>
        <button type="button" class="btn ghost compact" data-add-ingredient>+ Nguyên liệu</button>
      </div>
    </div>`;
  }

  function create(mount, options) {
    const item = options.item || null;
    const categories = (options.categories || []).filter(category => category.database_id);
    const editorData = options.editorData || {recipes:[], ingredients:[]};
    // Which glasses may be chosen. Safe here: it reads only editorData.
    const glasses = editorData.glasses || [];
    const drinkTypes = editorData.drink_types || [];
    const ingredients = editorData.ingredients || [];
    const recipe = item
      ? (editorData.recipes || []).find(value => Number(value.drink?.drink_id) === Number(item.id))
      : null;
    const drink = recipe?.drink || {};
    // Read AFTER `drink` exists. It was above the declaration, which is a
    // temporal dead zone -- `const drink` is hoisted but unreadable until
    // its line runs, so touching it earlier throws a ReferenceError and
    // create() died before rendering anything. That is why Edit and
    // "Thêm món" opened nothing at all.
    const glassId = drink.glass_id ?? null;
    const drinkTypeId = drink.drink_type_id ?? null;
    const typeById = id => drinkTypes.find(
      type => Number(type.drink_type_id) === Number(id)) || null;
    let selectedType = typeById(drinkTypeId);
    /* Which boxes start ticked.
       A drink's categories are a SET, not a first choice plus extras. This
       used to be a `categoryId` for the one <select> plus a hidden
       `secondaryCategoryIds` carried along so the others survived a save --
       which meant a drink in Summer AND Tea showed only one of them, and
       the other could not be removed from this screen at all.

       Three sources, in order: what the drink actually has; the category
       the menu list had it under, for a row opened before its recipe
       loaded; and for a brand new drink, the first one, so the form starts
       valid rather than starting with an error nobody has earned yet. */
    const selectedCategoryIds = new Set(
      (drink.category_ids?.length
        ? drink.category_ids
        : [categories.find(category => category.id === item?.catId)?.database_id
           ?? (item ? null : categories[0]?.database_id)]
      ).map(Number).filter(id => id > 0)
    );
    const steps = recipe?.steps?.length ? recipe.steps : [{}];

    mount.innerHTML = `
      <h3>${item ? 'Sửa món và công thức' : 'Thêm món và công thức'}</h3>
      <div class="msub">Dữ liệu được lưu trực tiếp vào MySQL.</div>
      <div class="editor-tabs">
        <button type="button" class="active" data-editor-tab="info">Thông tin món</button>
        <button type="button" data-editor-tab="recipe">Công thức</button>
      </div>
      <section data-editor-panel="info">
        <div class="mfield"><label>Tên món</label><input data-field="name" value="${escapeHtml(drink.name ?? item?.name ?? '')}"></div>
        <div class="mfield"><label>Giá</label><input data-field="price" type="number" min="0" step="0.01" value="${escapeHtml(drink.price ?? item?.price ?? 0)}"></div>
        <div class="mfield">
          <label>Danh mục</label>
          <!-- Not a <select multiple>. That attribute makes the browser
               render a permanently open listbox -- there is no native way
               to have a multi-select that collapses and drops down. So the
               closed state is a button dressed as a select, and the open
               state is a panel of real checkboxes underneath it. -->
          <div class="dropselect" data-dropselect data-field="categories">
            <button type="button" class="dropselect-field" data-dropselect-field>
              <span class="dropselect-summary" data-dropselect-summary></span>
              <span class="dropselect-caret" aria-hidden="true">&#9662;</span>
            </button>
            <div class="dropselect-menu" data-dropselect-menu>
              ${categories.map(category => {
                const id = Number(category.database_id);
                const name = escapeHtml(String(category.name).replace(/ Menu$/, ''));
                return `<label class="dropselect-option">
                  <input type="checkbox" value="${id}" data-name="${name}"
                         ${selectedCategoryIds.has(id) ? 'checked' : ''}>
                  <span>${name}</span>
                </label>`;
              }).join('')}
            </div>
          </div>
          <div class="mhint">Bấm để mở danh sách, tick nhiều danh mục tùy ý. Món sẽ hiện trong mọi danh mục được chọn trên màn hình khách.</div>
        </div>
        <div class="mfield">
          <label>Ly phục vụ</label>
          <select data-field="glass">
            <option value="">— Chưa đặt —</option>
            ${glasses.map(glass => `<option value="${Number(glass.glass_id)}" ${
              Number(glass.glass_id) === Number(glassId) ? 'selected' : ''
            }>#${String(glass.glass_id).padStart(4, '0')} · ${escapeHtml(glass.glass_name)}${
              glass.capacity_ml ? ` (${Number(glass.capacity_ml)} ml)` : ''
            }</option>`).join('')}
          </select>
          <div class="mhint">Màn hình pha chế sẽ hướng dẫn nhân viên lấy đúng ly này trước khi máy chạy. Bỏ trống thì bỏ qua bước đó.</div>
          <!-- Whether the recipe fits the glass. Filled by paintGlassFit()
               and hidden until there is something to compare. -->
          <div class="capfit" data-glass-fit hidden></div>
        </div>
        <div class="mfield">
          <label>Kiểu pha &amp; đá</label>
          <select data-field="drink-type">
            <option value="">— Chưa đặt —</option>
            ${drinkTypes.map(type => `<option value="${Number(type.drink_type_id)}" ${
              Number(type.drink_type_id) === Number(drinkTypeId) ? 'selected' : ''
            }>#${String(type.drink_type_id).padStart(4, '0')} · ${escapeHtml(type.type_name)}${
              type.method ? ` — ${escapeHtml(type.method)}` : ''
            }</option>`).join('')}
          </select>
          <div class="mhint">Loại đá và cách dựng ly, hiện ngay cạnh hình ly trên màn hình pha chế. Dụng cụ đi kèm lấy theo lựa chọn này.</div>
          <!-- The description belongs to the KIND of build, not to this
               drink, so editing it here changes every drink of that kind.
               The count under the box is what makes that plain before the
               save instead of after. -->
          <textarea data-field="drink-type-detail" rows="2" maxlength="200"
                    placeholder="Mô tả cách pha, hiện trên màn hình pha chế…"
          >${escapeHtml(selectedType?.detail ?? '')}</textarea>
          <div class="mhint" data-drink-type-hint>${detailHint(selectedType)}</div>
        </div>
        <div class="mfield">
          <label>Trang trí</label>
          <input data-field="garnish" maxlength="120"
                 value="${escapeHtml(drink.garnish ?? '')}"
                 placeholder="Ống hút to, lá bạc hà…">
          <div class="mhint">Riêng của món này. Bỏ trống thì màn hình pha chế không hiện ô trang trí.</div>
        </div>
        <div class="mfield">
          <label>Ảnh món</label>
          <div class="imgpick">
            <div class="imgpick-now" data-image-preview></div>
            <div class="imgpick-side">
              <div class="imgpick-name" data-image-name></div>
              <div class="imgpick-btns">
                <label class="btn ghost compact">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 8.5A2 2 0 0 1 5 6.5h2l1.4-2h7.2L17 6.5h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><circle cx="12" cy="13" r="3.5"/></svg> Tải ảnh lên
                  <input type="file" accept="image/*" data-image-file hidden>
                </label>
                <button type="button" class="btn ghost compact" data-image-browse>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4l2 2.5h7A1.5 1.5 0 0 1 19 10v7.5A1.5 1.5 0 0 1 17.5 19h-13A1.5 1.5 0 0 1 3 17.5Z"/></svg> Chọn ảnh có sẵn
                </button>
                <button type="button" class="btn ghost compact" data-image-clear>
                  Bỏ ảnh
                </button>
              </div>
            </div>
          </div>
          <!-- The path is what actually gets saved. Kept visible and
               editable, because somebody who knows the filename should not
               have to click through a gallery to type it. -->
          <input data-field="image" class="imgpick-path"
                 value="${escapeHtml(drink.image ?? item?.image ?? '')}"
                 placeholder="recipe/image/Drink.webp">
          <div class="imglib" data-image-library hidden></div>
        </div>
        <label class="available-field"><input data-field="available" type="checkbox" ${(drink.available ?? item?.available ?? true) ? 'checked' : ''}> Mở bán thủ công</label>
      </section>
      <section data-editor-panel="recipe" hidden>
        <div class="recipe-help">Mọi nguyên liệu đều hiện ở đây. Nguyên liệu <b>(thủ công)</b> không có bơm — máy sẽ dừng và nhờ nhân viên thêm ở bước đó.
          <br>Kéo nút chấm ở đầu mỗi bước để đổi thứ tự, hoặc bấm vào nút đó rồi dùng phím <b>\u2191</b> <b>\u2193</b>.</div>
        <!-- The whole builder shuts too, down to this one bar. The recipe
             is the taller half of a two-tab form: folded away, the fields
             above it -- name, price, glass, picture -- are all on screen at
             once, which is the state most edits actually start from. -->
        <div class="steps-box" data-steps-box>
          <div class="steps-head">
            <button type="button" class="steps-toggle" data-steps-toggle aria-expanded="true"
                    title="Thu gọn hoặc mở lại toàn bộ công thức">
              <svg class="chev" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="m9 5.5 7 6.5-7 6.5"/>
              </svg>
              <strong>Công thức</strong>
              <span class="steps-count" data-steps-count></span>
            </button>
            <button type="button" class="btn ghost compact" data-collapse-all>Thu gọn tất cả</button>
          </div>
          <!-- The SAME line as the one under the glass picker, painted by
               the same function. The glass is chosen on one tab and the
               grams are typed on the other, so a warning that lived only
               beside the picker would be invisible to the person actually
               making the recipe too big. -->
          <div class="capfit" data-glass-fit hidden></div>
          <div data-step-list>${steps.map((step, index) =>
            step.action ? actionStep(step, index) : recipeStep(ingredients, step, index)
          ).join('')}</div>
          <div class="step-adds">
            <button type="button" class="btn ghost" data-add-step>+ Thêm bước bơm</button>
            <button type="button" class="btn ghost" data-add-action-step>+ Thêm bước thao tác</button>
          </div>
        </div>
      </section>
      <div class="editor-error" data-editor-error hidden></div>
      <div class="modal-acts">
        <button type="button" class="btn ghost" data-editor-cancel>Hủy</button>
        <button type="button" class="btn primary" data-editor-save>Lưu vào database</button>
      </div>`;

    /* ---------- the picture ----------
       Three ways to set it, all landing on the same text field: upload a
       file, pick one already on the machine, or type the path. The
       preview reads that field, so however it was set it looks the same. */
    const imageField = () => mount.querySelector('[data-field="image"]');

    const paintImage = () => {
        const value = (imageField().value || "").trim();
        const preview = mount.querySelector("[data-image-preview]");
        const label = mount.querySelector("[data-image-name]");

        if (!value) {
            preview.innerHTML = '<span class="imgpick-empty">Chưa có ảnh</span>';
            label.textContent = "Món sẽ hiện bằng biểu tượng thay cho ảnh.";
            return;
        }

        // Stored relative to the project root; this page is one level down.
        const url = /^(?:https?:|\/|\.\.\/)/.test(value) ? value : "../" + value;
        preview.innerHTML =
            `<img src="${escapeHtml(url)}" alt="" ` +
            `onerror="this.replaceWith(Object.assign(document.createElement('span'),` +
            `{className:'imgpick-empty',textContent:'Không tìm thấy ảnh'}))">`;
        label.textContent = value.split("/").pop();
    };

    const setImage = path => {
        imageField().value = path;
        paintImage();
    };

    async function loadLibrary() {
        const box = mount.querySelector("[data-image-library]");
        box.hidden = false;
        box.innerHTML = '<div class="imglib-note">Đang tải…</div>';

        try {
            const response = await fetch("../api/images", {
                cache: "no-store",
                headers: { Authorization: "Bearer " + AdminAuth.token() },
            });
            const result = await response.json().catch(() => ({}));

            if (!response.ok || !result.ok) {
                throw new Error(result.error || "Không tải được thư viện ảnh.");
            }

            if (!result.images.length) {
                box.innerHTML =
                    '<div class="imglib-note">Chưa có ảnh nào. Bấm "Tải ảnh lên".</div>';
                return;
            }

            const current = (imageField().value || "").trim();
            box.innerHTML = result.images.map(image => `
                <button type="button" class="imglib-item${
                    image.path === current ? " active" : ""}"
                        data-pick="${escapeHtml(image.path)}"
                        title="${escapeHtml(image.name)}">
                  <img src="${escapeHtml(image.url)}" alt="" loading="lazy">
                  <span>${escapeHtml(image.name)}</span>
                </button>`).join("");

            box.querySelectorAll("[data-pick]").forEach(button => {
                button.onclick = () => {
                    setImage(button.dataset.pick);
                    box.querySelectorAll(".imglib-item").forEach(other =>
                        other.classList.toggle("active", other === button));
                };
            });
        } catch (error) {
            box.innerHTML =
                `<div class="imglib-note">${escapeHtml(error.message)}</div>`;
        }
    }

    /* Put one clip on one step: the hidden field the save reads, plus the
       two things the eye reads. Scoped to a step node because a recipe may
       hold several action steps and each keeps its own clip. */
    function setStepMedia(stepNode, src) {
        stepNode.querySelector('[data-media-src]').value = src || '';
        stepNode.querySelector('[data-media-name]').textContent =
            src || 'Chưa chọn phim';
        stepNode.querySelector('[data-media-preview]').innerHTML = mediaTile(src);
    }

    /* Its own gallery, not the drink photo one. A clip and a menu tile are
       never interchangeable, and one list holding both would invite
       picking a photo as a demonstration because it was simply there. */
    async function loadMediaLibrary(stepNode) {
        const box = stepNode.querySelector('[data-media-library]');
        box.hidden = false;
        box.innerHTML = '<div class="imglib-note">Đang tải…</div>';

        try {
            const response = await fetch("../api/medias", {
                cache: "no-store",
                headers: { Authorization: "Bearer " + AdminAuth.token() },
            });
            const result = await response.json().catch(() => ({}));

            if (!response.ok || !result.ok) {
                throw new Error(result.error || "Không tải được thư viện phim.");
            }

            if (!result.media.length) {
                box.innerHTML =
                    '<div class="imglib-note">Chưa có phim nào. Bấm "Tải phim lên".</div>';
                return;
            }

            const current = stepNode.querySelector('[data-media-src]').value.trim();
            box.innerHTML = result.media.map(clip => `
                <button type="button" class="imglib-item${
                    clip.src === current ? " active" : ""}"
                        data-pick-media="${escapeHtml(clip.src)}"
                        title="${escapeHtml(clip.name)}">
                  ${clip.kind === "video"
                      ? `<video src="${escapeHtml(clip.url)}" muted playsinline
                                preload="metadata"></video>`
                      : `<img src="${escapeHtml(clip.url)}" alt="" loading="lazy">`}
                  <span>${escapeHtml(clip.name)}</span>
                </button>`).join("");

            box.querySelectorAll("[data-pick-media]").forEach(button => {
                button.onclick = () => {
                    setStepMedia(stepNode, button.dataset.pickMedia);
                    box.querySelectorAll(".imglib-item").forEach(other =>
                        other.classList.toggle("active", other === button));
                };
            });
        } catch (error) {
            box.innerHTML =
                `<div class="imglib-note">${escapeHtml(error.message)}</div>`;
        }
    }

    /* One clip for one action step. Unlike a drink photo there is no
       library to pick from: a clip belongs to the step that names it, and
       offering a gallery would invite reusing a shake clip on a garnish
       step because it happened to be there. */
    async function uploadMedia(file, stepNode) {
        const label = stepNode.querySelector('[data-media-name]');
        const previous = label.textContent;
        label.textContent = `Đang tải ${file.name}…`;

        try {
            const response = await fetch(
                "../api/media?name=" + encodeURIComponent(file.name), {
                    method: "POST",
                    headers: {
                        Authorization: "Bearer " + AdminAuth.token(),
                        "Content-Type": file.type || "application/octet-stream",
                    },
                    body: file,
                });
            const result = await response.json().catch(() => ({}));

            if (!response.ok || !result.ok) {
                throw new Error(result.error || "Tải phim lên thất bại.");
            }

            setStepMedia(stepNode, result.name);

            // The new clip is now in the library, so refresh it if open.
            if (!stepNode.querySelector('[data-media-library]').hidden) {
                loadMediaLibrary(stepNode);
            }

            // Accepted, but worth saying out loud -- a heavy GIF still
            // plays, it just costs ten times what an MP4 would.
            if (result.warning) showError(new Error(result.warning));
        } catch (error) {
            label.textContent = previous;
            showError(error);
        }
    }

    async function uploadImage(file) {
        const label = mount.querySelector("[data-image-name]");
        label.textContent = `Đang tải ${file.name}…`;

        try {
            const response = await fetch(
                "../api/image?name=" + encodeURIComponent(file.name), {
                    method: "POST",
                    headers: {
                        Authorization: "Bearer " + AdminAuth.token(),
                        "Content-Type": file.type || "application/octet-stream",
                    },
                    body: file,
                });
            const result = await response.json().catch(() => ({}));

            if (!response.ok || !result.ok) {
                throw new Error(result.error || "Tải ảnh lên thất bại.");
            }

            setImage(result.path);

            // The new file is now in the library, so refresh it if it is open.
            if (!mount.querySelector("[data-image-library]").hidden) {
                loadLibrary();
            }
        } catch (error) {
            showError(error);
            paintImage();
        }
    }

    /* What the collapsed field reads. A dropdown that stays shut is only
       useful if it says what is inside it, so the summary is the list of
       ticked names -- not "3 selected", which makes you open it to find
       out which three. */
    const paintCategorySummary = () => {
      const box = mount.querySelector('[data-dropselect-summary]');
      const names = [...mount.querySelectorAll(
        '[data-field="categories"] input:checked')].map(input => input.dataset.name);
      box.textContent = names.length ? names.join(', ') : 'Chưa chọn danh mục';
      box.classList.toggle('empty', !names.length);
    };

    const showError = error => {
      const box = mount.querySelector('[data-editor-error]');
      box.textContent = error?.message || String(error);
      box.hidden = false;
      /* "Bước 3 phải có ít nhất một nguyên liệu" is no use at all while
         bước 3 is folded shut, so an error opens everything back up. The
         message names a step; the step has to be there to be looked at. */
      revealAll();
    };
    const renumber = () => {
      const all = mount.querySelectorAll('[data-recipe-step]');
      all.forEach((step, index) => {
        step.querySelector('[data-step-number]').textContent = String(index + 1);
      });
      // What the builder's head says when the builder is shut, so folding it
      // away never hides how much is in there.
      mount.querySelector('[data-steps-count]').textContent =
        `${all.length} bước`;
    };
    /* ---------- does the recipe fit the glass? ----------
       glass.capacity_ml had no reader on the machine at all: it was a
       number in a dropdown label and nothing more. This is what makes it
       answer a question -- will what this recipe pours go in the glass
       somebody just picked for it.

       1 g = 1 ml, AND THAT IS AN APPROXIMATION
           The recipe is in grams, the glass is in millilitres, and the
           honest conversion needs the density of every ingredient --
           syrup is roughly 1.3 g/ml, so a syrup-heavy drink really takes
           LESS room than this says. There is no density column and
           inventing one would be a bigger change than this is worth, so
           the ratio is fixed at 1 and SAID OUT LOUD in the line itself.
           A number somebody can see the assumption behind is worth more
           than a precise one they have to trust.

       IT WARNS, IT DOES NOT REFUSE
           Nothing here blocks the save, and the server is not asked to
           check it either. Ice displaces liquid, some drinks are served
           deliberately short, and a bar knows its own glassware -- a
           console that refused a recipe the shop actually makes would be
           wrong more often than the recipe is. It states the arithmetic
           and leaves the decision where it belongs.

       WHAT IT COUNTS
           Every gram in every pour step, manual ingredients included:
           they go in the same glass whether a pump or a person puts them
           there. Action steps hold no ingredient rows, so they
           contribute nothing without being special-cased. */
    const ML_PER_GRAM = 1;

    const glassById = id => glasses.find(
      glass => Number(glass.glass_id) === Number(id)) || null;

    /* Read off the DOM, not through readDocument(): that one runs the
       save-time validation and THROWS on a half-typed form -- an empty
       name, a gram field mid-edit. This has to survive every keystroke,
       so it sums what is there and ignores what is not yet a number. */
    const pouredGram = () => [...mount.querySelectorAll('[data-target-gram]')]
      .reduce((total, input) => {
        const gram = Number(input.value);
        return total + (Number.isFinite(gram) && gram > 0 ? gram : 0);
      }, 0);

    const paintGlassFit = () => {
      const boxes = mount.querySelectorAll('[data-glass-fit]');
      if (!boxes.length) return;      // the modal has already been closed

      const field = mount.querySelector('[data-field="glass"]');
      const glass = field ? glassById(field.value) : null;
      const capacity = Number(glass?.capacity_ml);
      const poured = pouredGram();

      // Nothing to say without both halves of the comparison: no glass
      // picked, a glass whose capacity nobody has filled in, or a recipe
      // that pours nothing yet.
      const known = glass && Number.isFinite(capacity) && capacity > 0 && poured > 0;

      // Rounded BEFORE the subtraction so the three numbers in the
      // sentence add up. Rounding afterwards prints "vượt 0 ml" for a
      // recipe that is over by a third of a millilitre.
      const millilitre = Math.round(poured * ML_PER_GRAM);
      const over = millilitre - capacity;

      // The name is quoted rather than prefixed with "ly": half the rows
      // are already called "Ly cao", "Ly martini", and the other half are
      // not called a ly at all -- "Ca đồng". Either way "ly Ca đồng" and
      // "ly Ly cao" are both wrong, and quotes are right for both.
      const text = !known ? ''
        : over > 0
          ? `Công thức rót ~${millilitre} ml, "${glass.glass_name}" chỉ chứa `
            + `${capacity} ml — vượt ${over} ml, chưa tính đá. `
            + 'Quy đổi 1 g = 1 ml.'
          : `Công thức rót ~${millilitre} ml, "${glass.glass_name}" chứa `
            + `${capacity} ml — còn ~${-over} ml cho đá. Quy đổi 1 g = 1 ml.`;

      boxes.forEach(box => {
        box.hidden = !known;
        box.classList.toggle('over', known && over > 0);
        // textContent: glass_name is whatever somebody typed into the
        // database, and it is a name, not markup.
        box.textContent = text;
      });
    };

    const readDocument = () => {
      const selectedCategories = [...mount.querySelectorAll(
        '[data-field="categories"] input:checked')].map(box => box.value);
      return buildDocument({
        drinkId:item?.id,
        name:mount.querySelector('[data-field="name"]').value,
        image:mount.querySelector('[data-field="image"]').value,
        price:mount.querySelector('[data-field="price"]').value,
        glassId:mount.querySelector('[data-field="glass"]').value,
        drinkTypeId:mount.querySelector('[data-field="drink-type"]').value,
        drinkTypeDetail:mount.querySelector('[data-field="drink-type-detail"]').value,
        garnish:mount.querySelector('[data-field="garnish"]').value,
        available:mount.querySelector('[data-field="available"]').checked,
        categoryIds:selectedCategories,
        steps:[...mount.querySelectorAll('[data-recipe-step]')].map(step => {
          if (step.dataset.stepKind === 'action') {
            const field = key => {
              const node = step.querySelector(`[data-action-field="${key}"]`);
              return node ? node.value : '';
            };
            return {
              ingredients:[],
              action:{
                media_src:step.querySelector('[data-media-src]').value,
                title_vi:field('title_vi'),
                title_en:field('title_en'),
                detail_vi:field('detail_vi'),
                detail_en:field('detail_en'),
                confirm_vi:field('confirm_vi'),
                confirm_en:field('confirm_en'),
                cup_returns:step.querySelector('[data-cup-returns]').checked,
              },
            };
          }
          return {
            ingredients:[...step.querySelectorAll('[data-recipe-ingredient]')].map(row => ({
              ingredientId:row.querySelector('[data-ingredient-id]').value,
              targetGram:row.querySelector('[data-target-gram]').value,
            })),
          };
        }),
      });
    };

    mount.onclick = async event => {
      /* The dropdown, before anything else.
         Ticking a box must NOT close the panel -- picking several
         categories is the whole point -- so a click inside the menu is
         left alone entirely; the summary follows the `change` event
         instead, wired below. Any other click in the modal closes an open
         panel and then carries on to whatever it was really for, which is
         what makes clicking the page dismiss the dropdown. */
      const dropField = event.target.closest('[data-dropselect-field]');
      if (dropField) {
        dropField.closest('[data-dropselect]').classList.toggle('open');
        return;
      }
      if (event.target.closest('[data-dropselect-menu]')) return;
      mount.querySelectorAll('[data-dropselect].open')
        .forEach(box => box.classList.remove('open'));

      const tab = event.target.closest('[data-editor-tab]');
      if (tab) {
        mount.querySelectorAll('[data-editor-tab]').forEach(button => button.classList.toggle('active', button === tab));
        mount.querySelectorAll('[data-editor-panel]').forEach(panel => { panel.hidden = panel.dataset.editorPanel !== tab.dataset.editorTab; });
        return;
      }
      if (event.target.closest('[data-editor-cancel]')) {
        options.onCancel?.();
        return;
      }
      if (event.target.closest('[data-image-browse]')) {
        const box = mount.querySelector('[data-image-library]');
        if (box.hidden) loadLibrary(); else box.hidden = true;
        return;
      }
      if (event.target.closest('[data-image-clear]')) {
        setImage('');
        return;
      }
      /* The lids. Before the buttons below, because a step's whole head is
         its own lid and the two "add" buttons sit outside every card. */
      const stepToggle = event.target.closest('[data-step-toggle]');
      if (stepToggle) {
        const step = stepToggle.closest('[data-recipe-step]');
        setShut(step, !isShut(step));
        paintCollapseAll();
        return;
      }
      if (event.target.closest('[data-steps-toggle]')) {
        setBoxShut(!isShut(stepsBox));
        return;
      }
      if (event.target.closest('[data-collapse-all]')) {
        const all = stepNodes();
        shutAll(!(all.length && all.every(isShut)));
        return;
      }
      if (event.target.closest('[data-add-step]')) {
        const list = mount.querySelector('[data-step-list]');
        list.insertAdjacentHTML('beforeend', recipeStep(ingredients, {}, list.children.length));
        // A step is added in order to be filled in, so it arrives open --
        // even when everything around it is folded away.
        renumber();
        paintCollapseAll();
        return;
      }
      if (event.target.closest('[data-add-action-step]')) {
        const list = mount.querySelector('[data-step-list]');
        list.insertAdjacentHTML('beforeend', actionStep({}, list.children.length));
        renumber();
        paintCollapseAll();
        return;
      }
      const mediaBrowse = event.target.closest('[data-media-browse]');
      if (mediaBrowse) {
        const step = mediaBrowse.closest('[data-recipe-step]');
        const box = step.querySelector('[data-media-library]');
        // Second press closes it, so the gallery is not left standing
        // open over the fields below it.
        if (!box.hidden) { box.hidden = true; return; }
        loadMediaLibrary(step);
        return;
      }
      const mediaClear = event.target.closest('[data-media-clear]');
      if (mediaClear) {
        setStepMedia(mediaClear.closest('[data-recipe-step]'), '');
        return;
      }
      const removeStep = event.target.closest('[data-remove-step]');
      if (removeStep) {
        const list = mount.querySelector('[data-step-list]');
        if (list.children.length <= 1) return showError(new Error('Công thức phải có ít nhất một bước.'));
        removeStep.closest('[data-recipe-step]').remove();
        renumber();
        paintCollapseAll();
        return;
      }
      const addIngredient = event.target.closest('[data-add-ingredient]');
      if (addIngredient) {
        addIngredient.closest('[data-recipe-step]').querySelector('[data-ingredient-list]')
          .insertAdjacentHTML('beforeend', ingredientRow(ingredients));
        return;
      }
      const removeIngredient = event.target.closest('[data-remove-ingredient]');
      if (removeIngredient) {
        const list = removeIngredient.closest('[data-ingredient-list]');
        if (list.children.length <= 1) return showError(new Error('Mỗi bước phải có ít nhất một nguyên liệu.'));
        removeIngredient.closest('[data-recipe-ingredient]').remove();
        return;
      }
      const save = event.target.closest('[data-editor-save]');
      if (!save) return;
      // Nothing is validated behind a closed lid: whatever the save has to
      // say about a step, that step is on screen to hear it.
      revealAll();
      const errorBox = mount.querySelector('[data-editor-error]');
      errorBox.hidden = true;
      save.disabled = true;
      const original = save.textContent;
      save.textContent = 'Đang lưu…';
      try {
        await options.onSave(readDocument());
      } catch (error) {
        showError(error);
      } finally {
        save.disabled = false;
        save.textContent = original;
      }
    };

    /* ---------- thu gọn / mở lại ----------
       Nothing here is hidden from the form: a folded step keeps every one
       of its inputs in the DOM, still holding its value, so readDocument()
       reads a shut card exactly as it reads an open one. Folding is a way
       of looking at a long recipe, never a way of leaving part of it out.

       It also pairs with the drag: fold the lot, and eight steps become
       eight short bars that can be put in order without scrolling once. */
    const stepList = mount.querySelector('[data-step-list]');
    const stepNodes = () => [...stepList.querySelectorAll(':scope > [data-recipe-step]')];
    const stepsBox = mount.querySelector('[data-steps-box]');
    const isShut = node => node.hasAttribute('data-collapsed');

    /* What a shut card has left to say. Written at the moment of closing
       rather than kept up to date while open -- the fields are the truth
       whenever they can be seen, and this only has to be right for as long
       as they cannot. */
    const summarise = step => {
      const box = step.querySelector('[data-step-summary]');
      if (step.dataset.stepKind === 'action') {
        const title = step.querySelector('[data-action-field="title_vi"]').value.trim();
        const media = step.querySelector('[data-media-src]').value.trim();
        box.textContent = title || (media ? media : 'chưa đặt tiêu đề');
        return;
      }
      // textContent, not innerHTML: an ingredient is named by whoever added
      // it to the database, and that name is not markup.
      box.textContent = [...step.querySelectorAll('[data-recipe-ingredient]')].map(row => {
        const name = row.querySelector('[data-ingredient-id]').selectedOptions[0];
        return `${name ? name.textContent.trim() : '?'} ${
          row.querySelector('[data-target-gram]').value}g`;
      }).join(' · ');
    };

    const setShut = (step, shut) => {
      if (shut) summarise(step);
      step.toggleAttribute('data-collapsed', shut);
      step.querySelector('[data-step-toggle]').setAttribute('aria-expanded', String(!shut));
    };

    /* One button for both directions: it offers whichever of the two is
       still worth doing. Two buttons would mean one of them was always
       greyed out or always a no-op. */
    const paintCollapseAll = () => {
      const all = stepNodes();
      mount.querySelector('[data-collapse-all]').textContent =
        all.length && all.every(isShut) ? 'Mở tất cả' : 'Thu gọn tất cả';
    };

    const shutAll = shut => {
      stepNodes().forEach(step => setShut(step, shut));
      paintCollapseAll();
    };

    const setBoxShut = shut => {
      stepsBox.toggleAttribute('data-collapsed', shut);
      mount.querySelector('[data-steps-toggle]').setAttribute('aria-expanded', String(!shut));
    };

    /* Everything open, at every level -- what an error needs, and what the
       save path needs before it complains about a field. */
    const revealAll = () => {
      setBoxShut(false);
      shutAll(false);
    };

    renumber();          // fills the count in the builder's head
    paintCollapseAll();

    /* ---------- đổi thứ tự các bước ----------
       Pointer events, not the HTML5 drag-and-drop API: this page is also
       opened on the machine's own touchscreen, where `dragstart` never
       fires at all. One code path here serves mouse, pen and finger.

       What travels is the step element itself, not a rendered copy of it.
       Carrying the real node takes the text already typed into it, its
       looping <video> and its file input along with it, so reordering
       cannot lose work that has not been saved yet. */
    /* The box that actually scrolls is the modal, not the page. Looked up
       when a drag starts rather than once up here: a short recipe does not
       overflow the modal until enough steps have been added to it. */
    const findScroller = () => {
      for (let node = stepList.parentElement; node; node = node.parentElement) {
        if (/(auto|scroll)/.test(getComputedStyle(node).overflowY) &&
            node.scrollHeight > node.clientHeight) return node;
      }
      return null;
    };

    let dragged = null;      // the step under the finger, null when idle
    let pointerY = 0;
    let scroller = null;
    let scrollStep = 0;      // px per frame; 0 unless the pointer is at an edge
    let scrollFrame = 0;

    /* Which step the dragged one belongs in front of: the first one whose
       MIDDLE sits below the pointer. Middles rather than edges, because a
       step should give up its place only once the pointer is properly past
       it -- edges make the list flip back and forth on a one-pixel move. */
    const dropBefore = () => stepNodes().find(node => node !== dragged &&
      pointerY < node.getBoundingClientRect().top + node.offsetHeight / 2) || null;

    /* No floating ghost: the list itself opens the gap, live, by moving the
       real card into place. With pour steps three lines tall and action
       steps a screen tall, a correctly sized gap says far more about where
       the step will land than a copy trailing the cursor would. */
    const reorder = () => {
      const before = dropBefore();
      if (before === dragged || before === dragged.nextElementSibling) return;
      stepList.insertBefore(dragged, before);
      renumber();
    };

    /* A finger held still at the edge of the modal sends no further move
       events, so the scrolling runs off a frame loop instead: it keeps
       going, and keeps re-sorting, for as long as the pointer stays put. */
    const EDGE = 56;
    const edgeSpeed = () => {
      if (!scroller) return 0;
      const box = scroller.getBoundingClientRect();
      if (pointerY < box.top + EDGE) return -Math.ceil((box.top + EDGE - pointerY) / 4);
      if (pointerY > box.bottom - EDGE) return Math.ceil((pointerY - box.bottom + EDGE) / 4);
      return 0;
    };
    const scrollTick = () => {
      scrollFrame = 0;
      if (!dragged || !scrollStep) return;
      const was = scroller.scrollTop;
      scroller.scrollTop += scrollStep;
      if (scroller.scrollTop !== was) reorder();
      scrollFrame = requestAnimationFrame(scrollTick);
    };

    /* Listened for on the window, not on the handle. A handle rides inside
       the card being moved, and moving a node in the DOM takes it out and
       puts it back -- which drops any pointer capture held on it, and with
       it the rest of the drag. The window is the one node no reorder can
       disturb. */
    const onPointerMove = event => {
      pointerY = event.clientY;
      reorder();
      scrollStep = edgeSpeed();
      if (scrollStep && !scrollFrame) scrollFrame = requestAnimationFrame(scrollTick);
    };
    const endDrag = () => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', endDrag);
      window.removeEventListener('pointercancel', endDrag);
      if (scrollFrame) cancelAnimationFrame(scrollFrame);
      scrollFrame = 0;
      scrollStep = 0;
      dragged?.classList.remove('dragging');
      stepList.classList.remove('reordering');
      dragged = null;
      renumber();
    };

    stepList.addEventListener('pointerdown', event => {
      const handle = event.target.closest('[data-step-drag]');
      // Right- and middle-clicks are not drags; a touch reports button 0
      // too, so the test is only applied to a mouse.
      if (!handle || (event.pointerType === 'mouse' && event.button !== 0)) return;
      dragged = handle.closest('[data-recipe-step]');
      pointerY = event.clientY;
      scroller = findScroller();
      dragged.classList.add('dragging');
      stepList.classList.add('reordering');
      // Stops the browser selecting the text of the cards being dragged
      // over; it also skips focusing the button, which is put back by hand
      // so the arrow keys below can carry on from where the drag stopped.
      // preventScroll, because a handle grabbed while only half on screen
      // would otherwise be scrolled into view under the finger -- the list
      // jumps, and the drag starts from somewhere the pointer is not.
      event.preventDefault();
      handle.focus({ preventScroll:true });
      window.addEventListener('pointermove', onPointerMove);
      window.addEventListener('pointerup', endDrag);
      window.addEventListener('pointercancel', endDrag);
    });

    /* The same handle, reached by keyboard: ↑ and ↓ move the step one place.
       The only way to reorder without a pointer, and the quicker way even
       with one when a step has to travel past a tall action card. */
    stepList.addEventListener('keydown', event => {
      const handle = event.target.closest('[data-step-drag]');
      if (!handle || (event.key !== 'ArrowUp' && event.key !== 'ArrowDown')) return;
      const step = handle.closest('[data-recipe-step]');
      const up = event.key === 'ArrowUp';
      const neighbour = up ? step.previousElementSibling : step.nextElementSibling;
      if (!neighbour) return;                 // already at that end
      event.preventDefault();                 // the modal must not scroll instead
      stepList.insertBefore(step, up ? neighbour : neighbour.nextElementSibling);
      renumber();
      handle.focus();                         // the move drops focus with the node
      handle.scrollIntoView({ block:'nearest' });
    });

    /* Delegated, because action steps are added after this runs and a
       direct listener would only ever reach the ones already on screen. */
    mount.addEventListener("change", event => {
        const input = event.target.closest("[data-media-file]");
        if (!input) return;
        const file = input.files && input.files[0];
        const step = input.closest("[data-recipe-step]");
        if (file && step) uploadMedia(file, step);
        input.value = "";        // so the same file can be picked twice
    });

    mount.querySelector("[data-image-file]").addEventListener("change", event => {
        const file = event.target.files && event.target.files[0];
        if (file) uploadImage(file);
        event.target.value = "";        // so the same file can be picked twice
    });
    imageField().addEventListener("input", paintImage);
    paintImage();

    /* `change`, not `click`. Clicking the LABEL of a checkbox fires a click
       that bubbles before the browser has flipped the box, then fires a
       second one from the input afterwards -- so a click-driven summary is
       briefly wrong and only right by accident of the second event.
       `change` fires once, after the state settles. */
    mount.querySelector('[data-dropselect-menu]')
      .addEventListener('change', paintCategorySummary);
    paintCategorySummary();

    /* Moving the picker swaps which row the description box is editing, so
       the box has to follow it -- otherwise text typed for "Đá viên" would
       be saved onto "Xay đá" the moment somebody changed their mind about
       the ice. Unsaved edits are kept per type in `pending`, so switching
       away and back does not silently lose what was typed. */
    const detailBox = mount.querySelector('[data-field="drink-type-detail"]');
    const detailHintBox = mount.querySelector('[data-drink-type-hint]');
    const pending = new Map();

    mount.querySelector('[data-field="drink-type"]')
      .addEventListener('change', event => {
        if (selectedType) pending.set(String(selectedType.drink_type_id), detailBox.value);

        selectedType = typeById(event.target.value);
        const key = selectedType ? String(selectedType.drink_type_id) : '';

        detailBox.value = pending.has(key)
          ? pending.get(key)
          : (selectedType?.detail ?? '');
        detailBox.disabled = !selectedType;
        detailHintBox.innerHTML = detailHint(selectedType);
      });

    detailBox.disabled = !selectedType;

    /* Repaint after anything that can move either half of the sum: typing
       in a gram field, changing the glass, adding or removing a step or
       an ingredient.

       THREE LISTENERS RATHER THAN SIX CALL SITES
           The alternative is a paintGlassFit() beside every mutation --
           add step, remove step, add ingredient, remove ingredient,
           reorder, and the glass picker. That is six places to remember,
           and the seventh one added later is the one that gets forgotten;
           the failure is a stale number on screen, which is worse than
           no number. The whole repaint is a sum over a handful of inputs
           in one modal, so paying it on every click is not a cost worth
           optimising.

       `click` matters on its own: adding or removing a row fires no
       input or change event. It is registered with addEventListener
       while the mutations above run off mount.onclick, so the property
       handler has already finished its DOM work by the time this reads
       it. */
    mount.addEventListener('input', paintGlassFit);
    mount.addEventListener('change', paintGlassFit);
    mount.addEventListener('click', paintGlassFit);
    paintGlassFit();

    return { readDocument, showError };
  }

  global.AdminRecipeEditor = { buildDocument, create };
})(window);
