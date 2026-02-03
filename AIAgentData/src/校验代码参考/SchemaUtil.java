package com.gaea.util.schema;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gaea.agent.pojo.Agent;
import com.gaea.agentpattern.pojo.AgentRunningPattern;
import com.gaea.check.pojo.SchemaError;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import nl.flotsam.xeger.Xeger;
import org.everit.json.schema.Schema;
import org.everit.json.schema.ValidationException;
import org.everit.json.schema.loader.SchemaLoader;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.json.JSONTokener;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * The type Schema util.
 *
 * @Author lrr
 * @Date 2024 /1/4 14:49
 */
@Component
public class SchemaUtil {
    @Value("${schema.agent}")
    private String agentSchemaPath;
    @Value("${schema.doctrine}")
    private String doctrineSchemaPath;
    @Value("${schema.agentPattern}")
    private String agentPatternPath;
    @Value("${schema.doe}")
    private String doeSchemaPath;





    /**
     * 校验Agent
     *
     * @param agents the agent
     * @return list
     */
    public Set<ValidationMessage> validateAgent(List<Agent> agents) {

        try {
            ObjectMapper mapper = new ObjectMapper();

            File schemaFile = new File(agentSchemaPath);

            JsonNode schemaNode = mapper.readTree(schemaFile);

            // 创建 JsonSchemaFactory 实例，指定 JSON Schema 版本为 draft-07
            JsonSchemaFactory factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V7);
            JsonSchema schema = factory.getSchema(schemaNode);

            // 读取要校验的 JSON 数据文件
            JsonNode dataNode = mapper.valueToTree(agents);

            // 进行校验
            Set<ValidationMessage> errors = schema.validate(dataNode);


            // 处理校验结果
            if (errors.isEmpty()) {
                System.out.println("数据校验通过");
            } else {
                System.out.println("数据校验失败：");
                for (ValidationMessage error : errors) {
                    System.out.println(error.getMessage());
                }
                return errors;
            }
        } catch (IOException e) {
            e.printStackTrace();

        }
        return null;
    }


    /**
     * 校验运行样式
     *
     * @param agentPatterns the agent pattern
     * @return list list
     */
    public Set<ValidationMessage> validateAgentPattern(List<AgentRunningPattern> agentPatterns) {
        try {
            ObjectMapper mapper = new ObjectMapper();

            File schemaFile = new File(agentPatternPath);

            JsonNode schemaNode = mapper.readTree(schemaFile);

            // 创建 JsonSchemaFactory 实例，指定 JSON Schema 版本为 draft-07
            JsonSchemaFactory factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V7);
            JsonSchema schema = factory.getSchema(schemaNode);

            // 读取要校验的 JSON 数据文件
            JsonNode dataNode = mapper.valueToTree(agentPatterns);

            // 进行校验
            Set<ValidationMessage> errors = schema.validate(dataNode);


            // 处理校验结果
            if (errors.isEmpty()) {
                System.out.println("数据校验通过");
            } else {
                System.out.println("数据校验失败：");
                for (ValidationMessage error : errors) {
                    System.out.println(error.getMessage());
                }
                return errors;
            }
        } catch (IOException e) {
            e.printStackTrace();

        }
        return null; // 返回错误列表
    }

    /**
     * 校验条令
     *
     * @param doctrine the doctrine
     * @return list list
     */
    public Set<ValidationMessage> validateDoctrine(Object doctrine) {
        try {
            ObjectMapper mapper = new ObjectMapper();

            File schemaFile = new File(doctrineSchemaPath);

            JsonNode schemaNode = mapper.readTree(schemaFile);

            // 创建 JsonSchemaFactory 实例，指定 JSON Schema 版本为 draft-07
            JsonSchemaFactory factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V7);
            JsonSchema schema = factory.getSchema(schemaNode);

            // 读取要校验的 JSON 数据文件
            JsonNode dataNode = mapper.valueToTree(doctrine);

            // 进行校验
            Set<ValidationMessage> errors = schema.validate(dataNode);


            // 处理校验结果
            if (errors.isEmpty()) {
                System.out.println("数据校验通过");
            } else {
                System.out.println("数据校验失败：");
                for (ValidationMessage error : errors) {
                    System.out.println(error.getMessage());
                }
                return errors;
            }
        } catch (IOException e) {
            e.printStackTrace();

        }
        return null; // 返回错误列表
    }


    /**
     * 校验DoE
     *
     * @param doe the doe
     * @return list list
     */
    public Set<ValidationMessage> validateDoe(Object doe) {
        try {
            ObjectMapper mapper = new ObjectMapper();

            File schemaFile = new File(doeSchemaPath);

            JsonNode schemaNode = mapper.readTree(schemaFile);

            // 创建 JsonSchemaFactory 实例，指定 JSON Schema 版本为 draft-07
            JsonSchemaFactory factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V7);
            JsonSchema schema = factory.getSchema(schemaNode);

            // 读取要校验的 JSON 数据文件
            JsonNode dataNode = mapper.valueToTree(doe);

            // 进行校验
            Set<ValidationMessage> errors = schema.validate(dataNode);


            // 处理校验结果
            if (errors.isEmpty()) {
                System.out.println("数据校验通过");
            } else {
                System.out.println("数据校验失败：");
                for (ValidationMessage error : errors) {
                    System.out.println(error.getMessage());
                }
                return errors;
            }
        } catch (IOException e) {
            e.printStackTrace();

        }
        return null; // 返回错误列表
    }


    /**
     * 获取String的类型
     *
     * @param path the path
     * @return string default value
     */
    public String getStringDefaultValue(String path) {
        ObjectMapper mapper = new ObjectMapper();

        // 读取 JSON Schema
        InputStream inputStream = getClass().getResourceAsStream(agentSchemaPath);


        // 将输入流转换为JSON对象
        try {
            JsonNode schemaNode = mapper.readTree(inputStream);

            // 解析JSON Pointer表达式

            String[] parts = path.split("/");

            // 2. 创建一个新的列表来存储修改后的路径部分
            StringBuilder newPath = new StringBuilder();

            // 3. 遍历每个部分并构建新的路径
            // 3. 遍历每个部分并构建新的路径
            JsonNode baseTargetNode = null;
            JsonNode patternTargetNode = null;

            for (int i = 1; i < parts.length; i++) {
                if (parts[i].matches("\\d+") || parts.equals("")) {
                    // 跳过索引部分
                    continue;
                }
                // 添加 "properties" 到当前部分
                newPath.append("/properties");
                newPath.append("/" + parts[i]);

                //判断该节点是否为数组

                String tempPath = newPath + "/items";
                baseTargetNode = schemaNode.at(tempPath);

                if (baseTargetNode.isArray()) {
                    newPath.append("/items/0");
                }

                if (i == parts.length - 1) {
                    baseTargetNode = schemaNode.at(newPath.toString());
                    patternTargetNode = baseTargetNode.at("/pattern");
                } else {
                    patternTargetNode = null;

                }
            }

            String pattern = patternTargetNode.asText();

            if (pattern == null || pattern.equals("")) {
                return "";
            } else {
                Xeger generator = new Xeger(pattern);
                String generate = generator.generate();
                String result = generate.replaceAll("[\\^\\$]", "");
                return result;
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        }

    }


    /**
     * 获取Schema的路径
     *
     * @param path the path
     * @return string
     */
    public static String modifyPath(String path) {
        // 1. 拆分路径
        String[] parts = path.split("/");

        // 2. 创建一个新的列表来存储修改后的路径部分
        StringBuilder newPath = new StringBuilder();


        // 3. 遍历每个部分并构建新的路径
        for (int i = 1; i < parts.length - 1; i++) {
            if (parts[i].matches("\\d+") || parts.equals("")) {
                // 跳过索引部分
                continue;
            }
            // 添加 "properties" 到当前部分
            newPath.append("/properties");
            newPath.append("/" + parts[i]);


            if (i == parts.length - 1) {
                newPath.append("/pattern");
            }
        }

        return newPath.toString();
    }


    /**
     * 判断一个String是否可以转换为json
     *
     * @param text the text
     * @return boolean
     */
    public boolean isValidJson(String text) {
        if (text == null) {
            return true;
        }
        try {
            new JSONObject(text);
        } catch (Exception ex) {
            // 如果是数组格式，尝试解析为JSONArray
            try {
                new JSONArray(text);
            } catch (Exception ex1) {
                return false;
            }
        }
        return true;
    }


    /**
     * The entry point of application.
     *
     * @param args the input arguments
     */
    public static void main(String[] args) {
        // 创建Test对象并赋值
//        Agent agent = new Agent();
//        SchemaUtil testSchema = new SchemaUtil();
//        List<Agent> allAgents = new ArrayList<Agent>();
//        allAgents.add(agent);
//        Agent agent1 = new Agent();
//        allAgents.add(agent1);
//        CheckAgent test = new CheckAgent();
//        test.setAgents(allAgents);
//        List<SchemaError> errors = testSchema.validate(test);

//        String path = "/agents/0/commStackConfig/commStacks/0/ commStackKey";
//        String s = modifyPath(path);
//        System.out.println(s);

//        String jsonString = "{\\\"name\\\":\\\"John\\\", \\\"age\\\":30}";
//        boolean isValidJson = isValidJson(jsonString);
//        System.out.println("字符串是否为有效的JSON格式: " + isValidJson);
    }


    /**
     * 获取某个节点的类型
     *
     * @param path the path
     * @return node type
     */
    public String getNodeType(String path) {
        ObjectMapper mapper = new ObjectMapper();

        // 读取 JSON Schema
        InputStream inputStream = getClass().getResourceAsStream(agentSchemaPath);


        // 将输入流转换为JSON对象
        try {
            JsonNode schemaNode = mapper.readTree(inputStream);

            // 解析JSON Pointer表达式

            String[] parts = path.split("/");

            // 2. 创建一个新的列表来存储修改后的路径部分
            StringBuilder newPath = new StringBuilder();

            // 3. 遍历每个部分并构建新的路径
            // 3. 遍历每个部分并构建新的路径
            JsonNode baseTargetNode = null;
            JsonNode TypeTargetNode = null;

            for (int i = 1; i < parts.length; i++) {
                if (parts[i].matches("\\d+") || parts.equals("")) {
                    // 跳过索引部分
                    continue;
                }
                // 添加 "properties" 到当前部分
                newPath.append("/properties");
                newPath.append("/" + parts[i]);

                //判断该节点是否为数组

                String tempPath = newPath + "/items";
                baseTargetNode = schemaNode.at(tempPath);

                if (baseTargetNode.isArray()) {
                    newPath.append("/items/0");
                }

                if (i == parts.length - 1) {
                    TypeTargetNode = schemaNode.at(newPath + "/type");
                }
            }

            String type = TypeTargetNode.asText();

            return type;
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}
