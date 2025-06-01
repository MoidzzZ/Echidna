let gamePlotNodes = {};
// 启动加载
let game;
let characters;

async function loadGameData() {
  try {
    const response = await fetch('./assets/plot_0524.json');
    gamePlotNodes = await response.json();
    initGame(); // 数据加载完成后初始化游戏
  } catch (error) {
    console.error('加载数据失败:', error);
  }
}

function initGame() {
    console.log(gamePlotNodes[plotIndex[0]]); // 使用数据
    const config = {
        type: Phaser.AUTO,
        width: 1200,
        height: 800,
        parent: 'gameContainer',
        scene: MainScene
    };

    game = new Phaser.Game(config);
}

loadGameData();

let plotIndex = [0];
let characterInfo = {};

const char_button= [
    {x: 150, y: 300, color: 0x3CB371},
    {x: 400, y: 300, color: 0x4169E1},
    {x: 650, y: 300, color: 0x6495ED},
    {x: 150, y: 600, color: 0xC71585},
    {x: 400, y: 600, color: 0x9370DB},
    {x: 650, y: 600, color: 0xFF69B4}
]

let title_list = [];
let prompt_list = [];
function load_characters_info(node_index_list){
    title_list = [];
    prompt_list = []
    // 展开node_index
    for (let i = 0; i < node_index_list.length; i++) {
        title_list.push(gamePlotNodes[node_index_list[i]]['node_info']);
        prompt_list.push(gamePlotNodes[node_index_list[i]]['characters']['三月七']);
    }
    const _time = gamePlotNodes[node_index_list[0]]['time'];
    const _location = gamePlotNodes[node_index_list[0]]['location'];
    dialogHistory.push(`GM: 
    当前情节主题："${title_list.join('<br>')}" 
    当前时间地点："${_time}，${_location}"
    可以参考的表演："${prompt_list.join('<br>') }"`);

    updateHistoryPanel(dialogHistory);

    characterInfo = {};
    characters = Object.keys(gamePlotNodes[node_index_list[0]]['characters']);
    // 按顺序遍历characters字典，将key作为characterInfo的key，然后按顺序读变量char_button的位置信息作为value
    characters.forEach((character, i) => {
        characterInfo[character] = {
            x: char_button[i].x,
            y: char_button[i].y,
            color: char_button[i].color
        };
    });
}


class MainScene extends Phaser.Scene {
    constructor() {
        super({ key: "MainScene" });
    }

    preload() {
        // 预加载所有角色图片
        const characters = ['march7', 'yanqin', 'yunli', 'mengming', 'scott', 'garden', 'teahouse']; // 替换为实际的角色名
        characters.forEach(char => {
            this.load.image(char.toLowerCase(), `./assets/${char.toLowerCase()}.png`);
        });
    }

    create() {
        // 初始化背景图片
        this.background = null; // 用于存储背景图片对象
        this.updateBackground('花园'); // 初始加载背景图片

        // 创建角色按钮
        this.characterButtons = this.add.group();
        load_characters_info([0]);
        this.updateCharacterButtons(Object.keys(characterInfo));

        // 创建控制按钮
        const buttonStyle = {
            fontSize: '20px',
            backgroundColor: '#800080',
            color: '#ffffff',
            padding: { x: 10, y: 5 },
            fixedWidth: 150
        };

        createButton(this, 560, 700, 'go plot', handleGoPlot, buttonStyle);
        stepButton = createButton(this, 750, 700, 'step', handleStep, buttonStyle);

        // 初始化显示历史记录
        updateHistoryPanel(dialogHistory);
    }

    updateCharacterButtons(characters) {
        // 清除旧按钮（保留事件监听）
        this.characterButtons.clear(true, true);

        // 更新背景图片
        if(plotIndex[0]>3){
            this.updateBackground('茶馆'); // 根据需要更新背景图片
        }
        else{
            this.updateBackground('花园'); // 根据需要更新背景图片
        }

        // 创建新按钮（复用原来的点击逻辑）
        characters.forEach(char => {
            // 创建圆形按钮
            const circle = this.add.circle(characterInfo[char].x, characterInfo[char].y, 40, characterInfo[char].color)
                .setInteractive()
                .setDepth(0); // 设置圆形的深度较低，确保图片在圆形上方

            // 创建金色边框
            const goldBorder = this.add.graphics();
            goldBorder.lineStyle(4, 0xFFFF00, 1); // 设置边框宽度为4，颜色为金色
            goldBorder.beginPath();
            goldBorder.arc(characterInfo[char].x, characterInfo[char].y, 40, 0, Math.PI * 2, false); // 绘制圆形边框
            goldBorder.strokePath(); // 绘制边框
            goldBorder.setDepth(0); // 设置边框的深度与圆形相同

            // 创建图片对象
            const image = this.add.image(characterInfo[char].x, characterInfo[char].y, char.toLowerCase())
                .setScale(0.8) // 根据图片大小调整缩放比例
                .setDepth(1); // 设置图片的深度较高，确保在圆形上方

            // 添加到统一管理的组
            this.characterButtons.add(circle);
            this.characterButtons.add(image);
            this.characterButtons.add(goldBorder); // 将金色边框添加到按钮组

            // 保持原有的交互逻辑
            circle.on('pointerdown', () => handleCharacterClick(char));
            circle.on('pointerover', () => {
                circle.setScale(1.1);
                circle.setFillStyle(0x808080);
            });
            circle.on('pointerout', () => {
                circle.setScale(1);
                circle.setFillStyle(characterInfo[char].color);
            });

            // 图片的交互逻辑（可选）
            image.on('pointerdown', () => handleCharacterClick(char));
            image.on('pointerover', () => {
                image.setScale(0.55); // 鼠标悬停时放大效果
            });
            image.on('pointerout', () => {
                image.setScale(0.5); // 鼠标移出时恢复原大小
            });
        });
    }

    updateBackground(imageKey) {
        // 如果背景图片已经存在，则移除
        if (this.background) {
            this.background.destroy();
        }

        // 创建新的背景图片
        this.background = this.add.image(450, 350, imageKey).setScale(1);
    }

    update() {
    }
}

function createButton(scene, x, y, text, callback, style) {
    const button = scene.add.text(x, y, text, style)
        .setInteractive()
        .setPadding(10)
        .setStyle(style)
        .setBackgroundColor(style.backgroundColor);

    button.on('pointerdown', callback);
    button.on('pointerover', () => button.setAlpha(0.8));
    button.on('pointerout', () => button.setAlpha(1));

    return button;
}


// 全局变量
let dialogHistory = [
    "GM: 您可以在下方输入框输入内容开始对话",
    "GM: 点击角色头像可以查看角色信息"
];

let stepButton;
let isStepButtonRed = false;
let speechBubbles = [];


function handleCharacterClick(characterName) {
    const historyDiv = document.getElementById('historyPanel');
    fetch('http://localhost:5001/char_info', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json', // 必须明确指定
        },
        body: JSON.stringify({
            character: characterName // 键名必须与后端一致（"character"）
        }),
        mode: 'cors', // 明确启用 CORS 模式
    })
    .then(response => {
        // 先检查HTTP状态码
        if (!response.ok) {
            return response.text().then(text => {
                throw new Error(`HTTP ${response.status}: ${text}`);
            });
        }
        return response.json();
    })
    .then(info => {
        // 构造角色信息HTML
        let characterInfoHTML;
        if (info['简历'] === '不是重要角色') {
            characterInfoHTML = `<div style="color: #000000">${characterName}: 不是重要角色</div>`;
        } else {
            const experiences = Array.isArray(info['经历'])
            ? info['经历'].join('<br>')  // 使用 <br> 换行
            : info['经历'] || '无';      // 如果不是数组，直接显示
            characterInfoHTML = `
                <div style="color: #000000"><strong>${characterName}的信息</strong></div>
                <div style="color: #000000">外观: ${info['外观'] || '无'}</div>
                <div style="color: #000000">简历: ${info['简历'] || '无'}</div>
                <div style="color: #000000">性格: ${info['性格'] || '无'}</div>
                <div style="color: #000000">经历: ${experiences}</div>
            `;
        }

        // 切换显示逻辑
        const currentContent = historyDiv.innerHTML.trim();
        if (currentContent === characterInfoHTML.trim()) {
            updateHistoryPanel(dialogHistory); // 假设这是你的历史记录恢复函数
        } else {
            historyDiv.innerHTML = characterInfoHTML;
        }
    })
    .catch(error => {
        console.error('完整错误信息:', error);
        historyDiv.innerHTML = `
            <div style="color: #ff0000">
                获取角色信息失败: ${error.message}
            </div>
        `;
    });
}

let index_dict = {};
let char_resp = [];


async function handleLoadNextPlot(index_dict) {
    console.log(index_dict);

    if (Object.keys(index_dict).length === 1) {
        plotIndex = index_dict[Object.keys(index_dict)[0]];
        load_characters_info(plotIndex)
        await sendRequest(plotIndex);
    } else{
        const dialog = document.createElement('dialog');
        dialog.style.padding = '20px';
        dialog.style.borderRadius = '10px';
        dialog.style.border = '1px solid #ccc';

        // 创建标题
        const title = document.createElement('h3');
        title.textContent = '场景发生了分歧，请选择下一个情节的性格偏好';
        title.style.marginBottom = '15px';
        dialog.appendChild(title);

        Object.keys(index_dict).forEach(key => {
            const button = document.createElement('button');
            button.textContent = key;
            button.style.margin = '5px';
            button.style.padding = '10px 20px';
            button.style.cursor = 'pointer';

            button.onclick = () => {
                plotIndex = index_dict[key]; // 更新plotIndex为选中选项对应的值
                dialog.close();
                dialog.remove();

                // 更新对话历史
                dialogHistory.push(`系统: 选择了 "${key}" 路线`);
                updateHistoryPanel(dialogHistory);
                load_characters_info(plotIndex)
                sendRequest(plotIndex);
            };

            dialog.appendChild(button);
        });

        // 将对话框添加到文档并显示
        document.body.appendChild(dialog);
        dialog.showModal();
    }
}

function updateDialogWithDelay(char_resp, index = 0) {
    if (index >= char_resp.length) {
        return; // 如果所有对话都处理完，结束递归
    }

    let [character, resp] = char_resp[index]; // 解构出角色和响应

    // 更新对话历史
    dialogHistory.push(`${character}: ${resp}`);
    updateHistoryPanel(dialogHistory);

    // 更新气泡
    clearSpeechBubbles();
    if (character !== "GM") {
        createSpeechBubble(character, resp);
    }

    // 使用 setTimeout 模拟延迟，并递归调用自身
    setTimeout(() => {
        updateDialogWithDelay(char_resp, index + 1); // 处理下一条对话
    }, 100); // 延迟 100 毫秒
}

async function sendRequest(plotIndex) {
    let data;
    if (plotIndex.length === 1) {
        if (plotIndex[0] === 999){
            alert('游戏已结束！');
            return;
        }

        await fetch('http://localhost:5001/next_plot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                next_index: plotIndex[0],
            }),
            mode: 'cors',
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(info => {
            data = info;
            console.log('Response data:', data);
            // 触发start_chat
            index_dict = data['node_index'];
            char_resp = data['char_resp'];
            updateDialogWithDelay(char_resp)
        })
        .catch(error => {
            console.error('Error during fetch operation:', error);
        });
    } else {
        await fetch('http://localhost:5001/next_mixed_plot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                node_index_list: plotIndex,
            }),
            mode: 'cors',
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(info => {
            data = info;
            console.log('Response data:', data);
            if (data['location'] === gamePlotNodes[plotIndex[0]]['location'] && data['time'] === gamePlotNodes[plotIndex[0]]['time']) {
                dialogHistory.push(`系统: 选择了 "${data['location']}" 路线`);
                updateHistoryPanel(dialogHistory);
            } else {
                alert('场景匹配错误');
            }
            clearSpeechBubbles();
        })
        .catch(error => {
            console.error('Error during fetch operation:', error);
        });
    }
}

let isHandlingStep = false; // 标志变量，用于防止重复触发
let isHandlingPlot = false; // 标志变量，用于防止重复触发
let isGoingPlot = false; // 标志变量，用于防止重复触发
let end_flag = true; // 标志变量，用于防止重复触发
let go_num=0


async function handleStep() {
    if (isHandlingStep) {
        console.log('Step is already being handled. Please wait.');
        return; // 如果正在处理，直接退出
    }

    isHandlingStep = true; // 设置标志为 true，表示正在处理

    try {
        if (isStepButtonRed) {
            clearSpeechBubbles();
            await handleLoadNextPlot(index_dict);

            const scene = game.scene.getScene("MainScene");
            scene.updateCharacterButtons(Object.keys(characterInfo));
            isStepButtonRed = false;
            stepButton.setBackgroundColor('#800080');
            return;
        }

        const inputText = document.querySelector('#inputText').value;

        // 添加用户输入到对话历史
        if (inputText.trim()) {
            createSpeechBubble('三月七', inputText);
            dialogHistory.push(`三月七: ${inputText}`);
        }

        // 根据当前 plotIndex 的大小，选择调用 chat 形式
        const url = plotIndex.length > 1
            ? 'http://localhost:5001/mixed_chat'
            : 'http://localhost:5001/chat';

        await fetchAndProcessResponse(url, inputText, data => {
            index_dict = data['node_index'];
            char_resp = data['char_resp'];

            document.querySelector('#inputText').value = '';
            updateDialogWithDelay(char_resp);

            // 如果 key 的数目等于 0，则说明节点没有发生变化
            // 当 key 的数目不为 0 时，说明情节变化，把按钮变红
            if (Object.keys(index_dict).length !== 0) {
                setStepButtonRed();
            }
        });
    } catch (error) {
        console.error('Error during handleStep:', error);
    } finally {
        isHandlingStep = false; // 无论成功或失败，都重置标志变量
    }
}

// 抽取公共逻辑：发送请求并处理响应
async function fetchAndProcessResponse(url, inputText, processData) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json', // 必须明确指定
        },
        body: JSON.stringify({
            content: inputText,
        }),
        mode: 'cors', // 明确启用 CORS 模式
    });

    if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();
    processData(data); // 处理返回的数据
}

function createSpeechBubble(character, text) {
    // 确保清除之前的气泡
    clearSpeechBubbles();

    const bubble = game.scene.scenes[0].add.graphics();

    // 调整气泡文本位置和样式
    const bubbleText = game.scene.scenes[0].add.text(
        characterInfo[character].x + 60,
        characterInfo[character].y - 40,
        text,
        {
            fontSize: '16px',
            fill: '#000',
            wordWrap: { width: 150 },
            align: 'center'
        }
    );

    // 调整气泡背景大小和位置
    const padding = 10;
    const bubbleWidth = Math.max(150, bubbleText.width + padding * 2);
    const bubbleHeight = Math.max(60, bubbleText.height + padding * 2);

    bubble.fillStyle(0xffffff, 1);
    bubble.lineStyle(2, 0x000000, 1);
    bubble.fillRoundedRect(
        characterInfo[character].x + 50,
        characterInfo[character].y - 50,
        bubbleWidth,
        bubbleHeight,
        10
    );
    bubble.strokeRoundedRect(
        characterInfo[character].x + 50,
        characterInfo[character].y - 50,
        bubbleWidth,
        bubbleHeight,
        10
    );

    // 调整气泡尖角位置
    bubble.beginPath();
    bubble.moveTo(characterInfo[character].x + 40, characterInfo[character].y);
    bubble.lineTo(characterInfo[character].x + 60, characterInfo[character].y - 20);
    bubble.lineTo(characterInfo[character].x + 80, characterInfo[character].y);
    bubble.closePath();
    bubble.fillPath();
    bubble.strokePath();

    speechBubbles.push(bubble, bubbleText);
}

async function handleGoPlot() {
    if (isHandlingPlot) {
        console.log('GoPlot is already being handled. Please wait.');
        return; // 如果正在处理，直接退出
    }
    isHandlingPlot = true; // 设置标志为 true，表示正在处理

    try {
        const inputText = document.querySelector('#inputText').value;

        // 添加用户输入到对话历史
        if (inputText.trim()) {

            clearSpeechBubbles()
            const url= 'http://localhost:5001/go_plot'
            await fetchAndProcessResponse(url, inputText, data => {
                index_dict = data['node_index'];
                document.querySelector('#inputText').value = '';
            });

            await handleLoadNextPlot(index_dict);
            const scene = game.scene.getScene("MainScene");
            scene.updateCharacterButtons(Object.keys(characterInfo));
        }
    } catch (error) {
        console.error('Error during handleStep:', error);
    } finally {
        isHandlingPlot = false; // 无论成功或失败，都重置标志变量
    }
}

async function goOnePlot() {
    if (isGoingPlot) {
        console.log('GoPlot is already being handled. Please wait.');
        return; // 如果正在处理，直接退出
    }
    isGoingPlot = true; // 设置标志为 true，表示正在处理

    try {

        // 添加用户输入到对话历史
        for (let i = 0; i <= 7; i++) {
            // 根据当前 plotIndex 的大小，选择调用 chat 形式
            while(go_num<5) {
                clearSpeechBubbles()
                const url = 'http://localhost:5001/go_plot'
                await fetchAndProcessResponse(url, String(i), data => {
                    index_dict = data['node_index'];
                    document.querySelector('#inputText').value = '';
                });

                Gm_info =[['GM', '情节'+i+'第'+(go_num+1)+'次循环开始']];
                updateDialogWithDelay(Gm_info);

                await handleLoadNextPlot(index_dict);
                const scene = game.scene.getScene("MainScene");
                scene.updateCharacterButtons(Object.keys(characterInfo));

                while (end_flag) {
                    // 根据当前 plotIndex 的大小，选择调用 chat 形式
                    const url = 'http://localhost:5001/go_one_plot';

                    await fetchAndProcessResponse(url, String(i), data => {
                        index_dict = data['node_index'];
                        char_resp = data['char_resp'];

                        updateDialogWithDelay(char_resp);

                        // 如果 key 的数目等于 0，则说明节点没有发生变化
                        // 当 key 的数目不为 0 时，说明情节变化，把按钮变红
                        if (Object.keys(index_dict).length !== 0) {
                            end_flag = false;
                        }
                    });
                }

                go_num = go_num+1;
                end_flag = true;
            }
            go_num = 0;
        }
    } catch (error) {
        console.error('Error during goOnePlot:', error);
    } finally {
        isGoingPlot = false; // 无论成功或失败，都重置标志变量
    }
}

function clearSpeechBubbles() {
    speechBubbles.forEach(item => item.destroy());
    speechBubbles = [];
}

function updateHistoryPanel(content) {
    const historyDiv = document.getElementById('historyPanel');
    if (Array.isArray(content)) {
        historyDiv.innerHTML = content.map(line => {
            const [speaker, ...message] = line.split(': ');
            let color = '#000000';
            if (speaker === 'GM') color = '#800080';
            else if (speaker === '三月七') color = '#0000FF';
            return `<div style="color: ${color}"><strong>${speaker}:</strong> ${message.join(': ')}</div>`;
        }).join('');
    } else {
        historyDiv.innerHTML = content.split('\n').map(line =>
            `<div style="color: #000000">${line}</div>`
        ).join('');
    }
    historyDiv.scrollTop = historyDiv.scrollHeight;
}

function setStepButtonRed() {
    isStepButtonRed = true;
    stepButton.setBackgroundColor('#FF0000');
}
